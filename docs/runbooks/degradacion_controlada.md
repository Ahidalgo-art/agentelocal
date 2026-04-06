# Runbook: Degradación controlada

> Cuando algo falla, queremos fallar elegantemente. Este runbook define cómo responder en diferentes escenarios de fallo.

---

## Niveles de degradación

### Nivel 1: Expected (esperado, modo normal)
**Ejemplos:**
- Cache expirado, vuelvo a cargar desde BD.
- Llamada a API externa lenta, reintento con backoff.

**Comportamiento:**
- Endpoint retorna HTTP 200 (éxito).
- Client ni se entera (transparente).
- Log: nivel INFO (no alarm).

**Implementación:**
```python
@app.get("/v1/orders/{id}")
async def get_order(id: str, db: Database):
    """
    Retorna order. Si cache falla, carga desde BD.
    """
    try:
        return cache.get(f"order:{id}")
    except CacheExpired:
        # Esperado
        order = db.query_order(id)
        cache.set(f"order:{id}", order)
        return order
```

---

### Nivel 2: Partial (degradación parcial)
**Ejemplos:**
- Order service cae, pero tenemos datos 1 hora vieja en caché.
- Geocoding API no responde, pero tenemos última locación conocida.

**Comportamiento:**
- Endpoint retorna HTTP 200 (parcial) **con flag `degraded: true`**.
- Incluir metadata: edad del dato, qué falta.
- Log: WARNING (monitor pero no alarm inmediato).

**Implementación:**
```python
@app.get("/v1/orders/{id}")
async def get_order(id: str):
    try:
        return await order_service.fetch_order(id)
    except OrderServiceUnavailable:
        # Parcial: retorna caché vieja con advertencia
        order = cache.get(f"order:{id}")
        return {
            **order,
            "degraded": True,
            "cache_age_seconds": 3600,
            "warning": "Order service currently unavailable, using cached data"
        }
```

**Contrato con cliente:**
- Client **debe** inspeccionar `degraded` field.
- Si está fallando un campo que el client necesita: client debe reintentar después (exponential backoff).

---

### Nivel 3: Critical (no disponible)
**Ejemplos:**
- BD principal completamente caída.
- Dependencia crítica no disponible y sin caché alternativo.

**Comportamiento:**
- Endpoint retorna **HTTP 503 Service Unavailable**.
- Header: `Retry-After: 60` (reintentar en 60 segundos).
- Response: mensaje amigable + trace_id.
- Log: ERROR + ALERT (escalada inmediata).

**Implementación:**
```python
@app.get("/v1/orders/{id}")
async def get_order(id: str):
    try:
        return await order_service.fetch_order(id)
    except OrderServiceUnavailable:
        # Sin fallback: critical
        logger.error(
            "Critical: order_service unavailable",
            extra={"trace_id": request.headers.get("X-Trace-ID"), "order_id": id}
        )
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "60"},
            content={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Order service is temporarily unavailable. Please try again in 1 minute.",
                "trace_id": request.headers.get("X-Trace-ID")
            }
        )
```

---

## Estrategia por componente

### 1. APIs externas (Nacex, Redur, Google Maps, etc.)

| Componente | Fallo | Nivel | Fallback | Retry |
|---|---|---|---|---|
| **Rate Quote API** | Timeout | Partial | Cached quote (max 1h old) | Exponential 1s, 2s, 4s |
| **Shipment Manifest** | 500 error | Critical | None | Max 3 attempts, fail → queue for later |
| **Geocoding** | No response | Partial | Last known location | Async retry (next 5 min) |
| **Tracking status** | Unavailable | Partial | Last status + "possibly updated" | Passive (next request) |

**Guardrail:** Si external API falla 3 veces en 5 minutos:
- Switch a "circuit breaker" mode.
- Log ALERT.
- Retorna Nivel 2 (partial) por los próximos 5 minutos.

---

### 2. Base de datos

| Escenario | Respuesta | Retry | Log |
|---|---|---|---|
| **Read timeout (>3s)** | Retorna HTTP 504 + retry-after 10s | 1 attempt automático | WARN |
| **Connection pool exhausted** | Queue request, retorna HTTP 503 | Retry en 30s | ERROR |
| **Primary down, replica good** | Read from replica + return `"read_only": true` | N/A | ALERT |
| **Both primary+replicas down** | HTTP 503 + retry-after 60s | None (wait for recovery) | CRITICAL |

**Contrato:** 
- Si get HTTP 503 con `read_only: true`, client puede intentar operaciones read-only.
- Si plain HTTP 503, client no puede hacer nada.

---

### 3. Cache (Redis/Memcached)

| Escenario | Acción | Nivel |
|---|---|---|
| **Cache miss (normal)** | Load from BD, set cache | 1 (expected) |
| **Cache expired (TTL)** | Load from BD, refresh | 1 (expected) |
| **Cache server timeout** | Skip cache, load from BD | 1 (expected) |
| **Cache server down (3+ fails)** | Disable cache for 5 min, load direct from BD | 2 (partial, slower) |

**No retornamos degraded en Nivel 1 porque es transparente.**

---

## Checklist por endpoint

Todo endpoint debe documentar:

```python
@app.get("/v1/orders/{id}")
async def get_order(id: str):
    """
    GET /v1/orders/{id}
    
    Retorna una orden por ID.
    
    Degradation scenarios:
    
    1. Order service timeout (3s)
      → Si tenemos caché, retorna caché + degraded: true
      → Si no, retorna HTTP 504 + retry-after 10s
      
    2. BD primary down
      → Retorna caché + degraded: true + read_only: true
      → Si no hay caché: HTTP 503 + retry-after 60s
      
    3. External API (tracking) fails
      → Retorna order sin tracking info + degraded: true
      → Client debe chequear "tracking" field
    
    Responsable: backend-core team
    Last updated: 2026-03-18
    """
```

---

## Testing degradación

### Unit tests
```python
def test_get_order_with_failed_tracking():
    """Si tracking API falla, retorna order + degraded flag"""
    service = OrderService(
        db=mock_db,
        tracking_api=FailingMock()  # Simula timeout
    )
    
    result = service.get_order("O-123")
    assert result["order_id"] == "O-123"
    assert result["degraded"] == True
    assert result["warning"] == "Tracking unavailable"

def test_get_order_with_db_down():
    """Si BD está down, retorna 503"""
    service = OrderService(
        db=DownMock(),
        cache=EmptyMock()
    )
    
    with pytest.raises(ServiceUnavailable) as exc:
        service.get_order("O-123")
    assert exc.value.retry_after == 60
```

### Integration tests (staging/prod-like)
- Destruir cache → verificar que BD toma el relevo.
- Cerrar conexión BD → verificar caché fallback.
- Simular timeout en API externa → verificar degradado.

---

## Observabilidad de degradaciones

Logs **obligatorios**:

```json
{
  "timestamp": "2026-03-18T10:30:45Z",
  "trace_id": "req-abc123",
  "level": "WARN",
  "message": "Partial degradation detected",
  "component": "order_service",
  "issue": "tracking_api_timeout",
  "fallback_used": "cached_tracking_30min_old",
  "endpoint": "GET /v1/orders/O-123",
  "client_sees": "degraded: true"
}
```

Métricas:

```python
# Prometheus/Grafana compatible
degradation_level_counter = Counter(
    'degradation_level',
    'Degradation level triggered',
    ['endpoint', 'level', 'component']
)

# Incrementar según corresponda
degradation_level_counter.labels(
    endpoint='/v1/orders/{id}',
    level='partial',
    component='tracking_api'
).inc()
```

---

## Escalada y alertas

| Nivel | Threshold | Acción | Alert to |
|---|---|---|---|
| **Level 1** | >5 eventos/min | Log INFO | None (baseline) |
| **Level 2** | >3 eventos/5min | Log WARN | Slack #backend |
| **Level 3** | >1 evento | Log ERROR | Slack #backend + PagerDuty |
| **Level 3** | >5 eventos/1hr | Incident | VP Engr + on-call engineer |

---

## Runbook de recuperación

Si degradación persiste >15 minutos:

1. **Diagnosticar:**
   ```powershell
   # Ver logs en tiempo real
   # (asumiendo CloudWatch/ELK)
   journalctl -f -u order-service | grep degradation
   
   # Check status dependencias
   curl http://localhost:8000/v1/health
   curl http://external-api.com/health
   ```

2. **Decisión:**
   - ¿Es fallo externo (proveedor)? → Informar a cliente, wait for recovery.
   - ¿Es fallo nuestro (BD/infra)? → Restaurar, validar, comunicar.

3. **Validación post-recovery:**
   ```bash
   # Verificar que normal level volvió
   grep "degraded.*false" logs.txt  # Debería haber eventos nuevos sin degradación
   
   # Smoke test
   curl -H "X-Trace-ID: recovery-test-123" http://localhost:8000/v1/health
   ```

4. **Post-incident:**
   - RCA (root cause analysis).
   - Lección aprendida → cambio en architecture/resilience.
   - Crear ADR si es decisión arquitectónica nueva.

---

## Última validación: ¿es elegante?

Preguntas que validar:

- [ ] ¿Client sabe qué significa `degraded: true`?
- [ ] ¿Hay retry policy documentada?
- [ ] ¿Logs son útiles para debug?
- [ ] ¿SLA de recuperación es realista?
- [ ] ¿Se testea degradación en CI?
- [ ] ¿Alertas van al channel correcto sin noise?

Si responden que sí a todas → **degradación = elegante y predecible.**
