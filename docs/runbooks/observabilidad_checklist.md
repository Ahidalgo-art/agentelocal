# Runbook: Observabilidad Checklist

> Toda feature debe ser observable. Este checklist asegura que "observable" no sea cosmético.

---

## Qué es observable

Consigna siguiente: **en producción, 3 años después, cuando alguien reporta un bug sin traces, queremos poder debuggearlo en 5 minutos, no 5 horas.**

Para eso:
- Logs con contexto (trace_id).
- Métricas de negocio (no solo técnicas).
- Errores estandarizados.
- Health checks funcionales.

---

## Checklist OBLIGATORIO por endpoint

Antes de marcar PR como DONE, **todos estos deben estar**:

### 1. Trace ID
```python
@app.get("/v1/orders/{id}")
async def get_order(id: str, request: Request):
    # OBLIGATORIO: extraer o generar trace_id
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    
    logger.info(f"Fetching order {id}", extra={"trace_id": trace_id})
    
    # En TODAS las respuestas
    response = JSONResponse(
        status_code=200,
        content={"order_id": id, "trace_id": trace_id}
    )
    response.headers["X-Trace-ID"] = trace_id
    return response
```

**Por qué:** Sin trace_id, no puedes correlacionar logs dispersos en BD, cache, API externa, etc.

---

### 2. Latencia y status code
```python
import time
from prometheus_client import Histogram, Counter

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'status']
)

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

@app.get("/v1/orders/{id}")
async def get_order(id: str):
    start = time.time()
    try:
        order = await db.get_order(id)
        status = 200
        return order
    except NotFound:
        status = 404
        raise
    except Exception as e:
        status = 500
        raise
    finally:
        duration = time.time() - start
        request_duration.labels(
            method='GET',
            endpoint='/v1/orders/{id}',
            status=status
        ).observe(duration)
        request_count.labels(
            method='GET',
            endpoint='/v1/orders/{id}',
            status=status
        ).inc()
        logger.info(
            f"Request completed",
            extra={
                "end
point": "/v1/orders/{id}",
                "status_code": status,
                "duration_ms": duration * 1000,
                "trace_id": trace_id
            }
        )
```

**Por qué:** Saberas que `GET /v1/orders/{id}` es lento (p99 > 500ms) sin tener que leer 1000 logs.

---

### 3. Error handling estandarizado
```python
@app.get("/v1/orders/{id}")
async def get_order(id: str):
    try:
        return await db.get_order(id)
    except OrderNotFound:
        return JSONResponse(
            status_code=404,
            content={
                "code": "ORDER_NOT_FOUND",  # PascalCase, sem espaços
                "message": f"Order {id} not found",
                "trace_id": trace_id  # OBLIGATORIO
            }
        )
    except Exception as e:
        # Never expose internal error details
        logger.error(
            "Unexpected error fetching order",
            exc_info=e,
            extra={"trace_id": trace_id, "order_id": id}
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "trace_id": trace_id
            }
        )
```

**Contrato de error response:**
```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "Order 123 was not found",
  "trace_id": "req-abc-123",
  "details": {  // Opcional, solo si hay info útil
    "order_id": "O-456",
    "timestamp": "2026-03-18T10:30:45Z"
  }
}
```

---

### 4. Business metrics
```python
# Contador: cuántas órdenes procesadas por tipo
orders_processed = Counter(
    'orders_processed_total',
    'Total orders processed',
    ['order_type', 'status']  # order_type = "urgent", "standard", etc
)

@app.post("/v1/orders")
async def create_order(req: OrderRequest):
    order = db.create_order(req)
    
    # Métrica de negocio: qué tipo de order se creó
    orders_processed.labels(
        order_type=req.type,
        status="created"
    ).inc()
    
    logger.info(
        f"Order created",
        extra={
            "order_id": order.id,
            "order_type": order.type,
            "trace_id": trace_id
        }
    )
    return order
```

**Diferencia:**
- **Métrica técnica:** `http_requests_total` (cuán activo está el server).
- **Métrica de negocio:** `orders_processed_total` (cuánta plata estamos haciendo).

Ambas importan.

---

### 5. Transitions lógicas
Si un orden pasa por estados (pending → processing → shipped):

```python
# Contador: transiciones de estado
order_transitions = Counter(
    'order_state_transitions_total',
    'Order state transitions',
    ['from_state', 'to_state', 'result']  # result = "success" o "failed"
)

async def update_order_status(order_id: str, new_state: str):
    old_state = order.state
    try:
        order.state = new_state
        db.save(order)
        
        order_transitions.labels(
            from_state=old_state,
            to_state=new_state,
            result="success"
        ).inc()
        
        logger.info(
            f"Order state transition",
            extra={
                "order_id": order_id,
                "from": old_state,
                "to": new_state,
                "trace_id": trace_id
            }
        )
    except Exception as e:
        order_transitions.labels(
            from_state=old_state,
            to_state=new_state,
            result="failed"
        ).inc()
        logger.error(f"Failed to transition order", exc_info=e, extra={"trace_id": trace_id})
        raise
```

---

## Health checks funcionales

### Endpoint: GET /v1/health

Retorna estado real, no cosmético:

```python
@app.get("/v1/health")
async def health():
    """
    Health check: verifica dependencias CRÍTICAS.
    
    Returns 200 si todas las dependencias esenciales están disponibles.
    Returns 503 si hay degradación critical.
    """
    
    checks = {}
    
    # Check: conexión a BD
    try:
        await db.execute("SELECT 1")
        checks["database"] = {"status": "up"}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)}
    
    # Check: conexión a Redis/cache
    try:
        await cache.ping()
        checks["cache"] = {"status": "up"}
    except Exception as e:
        checks["cache"] = {"status": "down", "error": str(e)}
    
    # Check: API externa crítico (si aplica)
    try:
        await external_api.health()
        checks["external_tracking"] = {"status": "up"}
    except Exception as e:
        checks["external_tracking"] = {"status": "down", "error": str(e)}
    
    # Decisión: ¿estamos operables?
    essential_down = ["database"]  # SI la BD cae → no operamos
    critical_down = all(dep in checks and checks[dep]["status"] == "down" for dep in essential_down)
    
    status_code = 503 if critical_down else 200
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if status_code == 200 else "degraded",
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }
    )
```

**Contrato:**
- 200 OK + `"status": "healthy"` → puedes servir requests
- 200 OK + `"status": "degraded"` → algunos servicios caídos, pero operamos al 60%
- 503 Service Unavailable → no trabujar, los clientes deben retry

---

## Logs: formato y contexto

### ✅ Buen log
```python
logger.info(
    "Order created successfully",
    extra={
        "trace_id": "req-abc-123",
        "order_id": "O-456",
        "customer_id": "C-789",
        "amount": 125.50,
        "order_type": "express",
        "processing_time_ms": 234
    }
)
# Output:
# 2026-03-18T10:30:45Z | INFO | Order created successfully | trace_id=req-abc-123 | order_id=O-456 | customer_id=C-789 | amount=125.50 | order_type=express | processing_time_ms=234
```

### ❌ Mal log
```python
logger.info(f"Order {order_id} was created")
# Output:
# 2026-03-18T10:30:45Z | INFO | Order O-456 was created
# (missing trace_id, customer_id, amount, type — no es possible debuggear)
```

---

## Configuración por entorno

### Development (local)
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s | %(extra)s'
)

# Prometheus metrics → stdout (para desarrollo)
# No centralizado
```

### Staging
```python
logging.basicConfig(
    level=logging.INFO,
    format='json'  # Estructura para ELK
)

# Prometheus → Grafana (ambiente compartido)
# Retención: 7 días
```

### Production
```python
logging.basicConfig(
    level=logging.INFO,
    format='json'
)

# CloudWatch / ELK con indexación por trace_id
# Retención: 30 días (adjust según SLA)
# Alertas SLO-bound
```

---

## Métricas que monitorear en dashboard

Crea un Grafana dashboard con:

```
Row 1: Salud del sistema
  - Uptime (99.x%)
  - Errores últimas 24h
  - Latencia p50, p95, p99

Row 2: Business metrics
  - Órdenes procesadas (total y por tipo)
  - Revenue (if applicable)
  - Conversión (clientes → órdenes)

Row 3: Degradations
  - Eventos Level 2 (partial) último día
  - Eventos Level 3 (critical) último día
  - MTTR (mean time to recovery)

Row 4: Dependencies
  - External API latency
  - Cache hit rate
  - DB connection pool utilization
```

---

## Verificación antes de DONE

Todo endpoint DEBE pasar esto:

- [ ] Trace ID en request headers y response
- [ ] Métricas de latencia registradas (prometheus)
- [ ] Error handling con `code` + `message` + `trace_id`
- [ ] Business metrics (si aplica)
- [ ] Health check actualizado para nuevas dependencias
- [ ] Logs estructurados (JSON-ready)
- [ ] Documentación: degradation scenario (ver runbook degradacion_controlada.md)
- [ ] Tests: errores propagan trace_id

Si falta alguno → **no está listo para producción.**

---

## Auditoría trimestral

Cada 3 meses, reviewar:

- [ ] ¿Tenemos visibilidad en los endpoints que importan?
- [ ] ¿Los logs ayudan a debuggear problemas o son ruido?
- [ ] ¿Metrics están bien nombradas vs business language?
- [ ] ¿SLA vs realidad: qué nos falta?
- [ ] ¿Hay endpoints "shadow" sin observabilidad?

Crear ticket si hay gaps.
