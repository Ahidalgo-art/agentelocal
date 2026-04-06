# Runbook: Data Governance

> Aunque hoy no manejes datos sensitivos, establecer buenas prácticas ahora evita deuda técnica mañana cuando sí los manejes.

---

## 1) Clasificación de datos

### Por nivel de sensibilidad

| Nivel | Ejemplos | Caducidad | Encriptación | Auditoría |
|---|---|---|---|---|
| **Public** | Catálogos, carreras públicas | Indefinida | No | No |
| **Internal** | Métricas operativas, logs | 90 días | En tránsito | Basic |
| **Restricted** | Direcciones de clientes, tel, email | 1 año (GDPR) | Reposo + tránsito | Mediana |
| **Confidential** | Passwords, API keys, tokens | Mínimo necesario | Reposo + tránsito + salt | Auditada |

**Hoy:** Los datos de `agente_local` son `Public` o `Internal`.  
**Mañana (si integras clientes):** Pasarán a ser `Restricted`.

---

## 2) Ciclo de vida de datos

### Ingesta (entrada)
```
Origen externo (Nacex API, CSV, form)
    ↓
  Validación (schema, tipos, ranges)
    ↓
  Sanitización (trim, SQL injection prevention)
    ↓
  Almacenamiento (DB)
    ↓
  Log auditoría (quién, cuándo, fuente)
```

**Regla:** Nunca confíes en datos externos. Valida siempre en la frontera.

```python
@app.post("/v1/import/rates")
async def import_rates(req: RateImportRequest):
    """
    Importa tarifas desde Nacex.
    
    Auditoría: todas las importaciones se loguean con
    - timestamp
    - user_id (quien disparó)
    - source (NACEX API versión X)
    - count (cuántos records)
    - checksum (integridad)
    """
    
    trace_id = generate_trace_id()
    
    # Validación y sanitización
    for rate in req.rates:
        if not is_valid_rate(rate):
            logger.error(
                "Invalid rate in import",
                extra={
                    "trace_id": trace_id,
                    "source": "nacex",
                    "rate": rate,
                }
            )
            return JSONResponse(
                status_code=400,
                content={"code": "INVALID_RATE", "trace_id": trace_id}
            )
    
    # Registro auditoría
    audit_log.insert({
        "action": "import_rates",
        "timestamp": now(),
        "user_id": request.user.id,
        "source": "nacex_api_v2",
        "count": len(req.rates),
        "checksum": hash(req.rates),
        "trace_id": trace_id,
        "ip_address": request.client.host
    })
    
    # Almacenar
    db.bulk_insert_rates(req.rates)
    
    logger.info(
        "Rates imported successfully",
        extra={
            "trace_id": trace_id,
            "count": len(req.rates),
            "import_id": import_id
        }
    )
```

---

### Acceso (lectura)
```
User solicita datos
    ↓
  ¿Tiene permiso? (role-based access control)
    ↓
  ¿Está auditado? (log quién accedió, cuándo)
    ↓
  ¿Es dato masivo? (limitar campos, paginar)
    ↓
  Retorno seguro
```

**Regla:** No retornes siempre todo. Retorna solo lo que se necesita.

```python
@app.get("/v1/orders")
async def list_orders(
    request: Request,
    skip: int = 0,
    limit: int = 100,  # Máximo 1000 para evitar queries explosivas
):
    """
    Lista órdenes del usuario autenticado.
    
    Contratos:
    - Cada user solo ve sus propias órdenes (role-based)
    - Máximo 1000 por request
    - Retorna solo: id, status, created_at (no full details aquí)
    - Log de acceso: quién, cuándo, cuántos registros
    """
    
    # Autenticación + autorización
    if not request.user:
        return JSONResponse(status_code=401, content={"code": "UNAUTHORIZED"})
    
    # Validación
    if limit > 1000:
        limit = 1000
    
    # Acceso: solo órdenes del usuario
    orders = db.query(
        "SELECT id, status, created_at FROM orders WHERE customer_id = ? LIMIT ? OFFSET ?",
        (request.user.id, limit, skip)
    )
    
    # Auditoría
    audit_log.insert({
        "action": "list_orders",
        "user_id": request.user.id,
        "count_returned": len(orders),
        "timestamp": now(),
        "ip_address": request.client.host
    })
    
    return {
        "orders": orders,
        "total_count": db.count_orders(request.user.id),
        "trace_id": trace_id
    }
```

---

### Modificación (update/delete)
```
User solicita cambio
    ↓
  ¿Tiene permiso de escribir?
    ↓
  ¿Qué cambió? (snapshot antes/después)
    ↓
  ¿Es reversible? (keep old version for 90 días)
    ↓
  Log auditoría completo
    ↓
  Almacenar
```

```python
@app.patch("/v1/orders/{id}")
async def update_order(id: str, req: OrderUpdateRequest):
    """
    Actualiza una orden.
    
    Auditoría: snapshot antes/después + quién hizo cambio
    """
    
    # Fetch original
    old_order = db.get_order(id)
    if not old_order:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND"})
    
    # Autorización: solo owner o admin puede cambiar
    if request.user.id != old_order.customer_id and not request.user.is_admin:
        logger.warn(
            "Unauthorized order update attempt",
            extra={
                "trace_id": trace_id,
                "user_id": request.user.id,
                "order_id": id,
                "ip_address": request.client.host
            }
        )
        return JSONResponse(status_code=403, content={"code": "FORBIDDEN"})
    
    # Update
    new_order = {**old_order, **req.dict()}
    db.update_order(id, new_order)
    
    # Auditoría: qué cambió
    changes = {
        key: (old_order.get(key), new_order.get(key))
        for key in new_order.keys()
        if old_order.get(key) != new_order.get(key)
    }
    
    audit_log.insert({
        "action": "update_order",
        "order_id": id,
        "user_id": request.user.id,
        "changes": changes,  # before/after per field
        "timestamp": now(),
        "trace_id": trace_id,
        "ip_address": request.client.host
    })
    
    logger.info(
        "Order updated",
        extra={
            "trace_id": trace_id,
            "order_id": id,
            "fields_changed": list(changes.keys())
        }
    )
    
    return new_order
```

---

### Eliminación (purga)
```
Política: cuándo eliminar datos
    ↓
  Backup (antes de borrar)
    ↓
  Borrado (física o soft-delete)
    ↓
  Log auditoría inmodificable
    ↓
  Retención (poder recuperar si error)
```

**Regla:** No borres nunca sin backup. Usa soft-delete primero.

```python
# Schema: añadir a todas las tablas
class BaseModel(Base):
    """
    Mixin: soft-delete support
    """
    deleted_at = Column(DateTime, nullable=True)  # NULL = activo, fecha = borrado
    deleted_by = Column(String, nullable=True)    # quién lo borró
    deletion_reason = Column(String, nullable=True)  # por qué

@app.delete("/v1/orders/{id}")
async def delete_order(id: str, req: DeleteRequest):
    """
    Soft-deletes una orden.
    
    No borra físicamente; marca con deleted_at + reason.
    Auditoría: quién, cuándo, por qué.
    Recuperable: admin puede undo en 30 días.
    """
    
    order = db.get_order(id)
    if not order:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND"})
    
    if request.user.id != order.customer_id and not request.user.is_admin:
        return JSONResponse(status_code=403, content={"code": "FORBIDDEN"})
    
    # Soft-delete
    db.execute(
        "UPDATE orders SET deleted_at = ?, deleted_by = ?, deletion_reason = ? WHERE id = ?",
        (now(), request.user.id, req.reason or "Manual deletion", id)
    )
    
    # Auditoría
    audit_log.insert({
        "action": "delete_order",
        "order_id": id,
        "deleted_by": request.user.id,
        "reason": req.reason,
        "timestamp": now(),
        "trace_id": trace_id
    })
    
    # Backup job scheduled (automático, daily)
    # recovery_service.register_for_recovery(order_id=id, days=30)
    
    logger.info(
        "Order soft-deleted",
        extra={
            "trace_id": trace_id,
            "order_id": id,
            "reason": req.reason,
            "recoverable_until": (now() + timedelta(days=30)).isoformat()
        }
    )
    
    return JSONResponse(status_code=200, content={"message": "Order deleted"})
```

**Physical deletion policy** (después de 30 días de soft-delete):
```python
# Job que corre daily
async def purge_soft_deleted_orders():
    """
    Elimina órdenes soft-deleted hace >30 días.
    
    Ejecuta:
    - Backup completo del orden a almacenamiento separado (S3, archivos)
    - Borrado físico de BD
    - Log inmutable de qué fue borrado
    """
    cutoff_date = now() - timedelta(days=30)
    
    orders_to_purge = db.query(
        "SELECT * FROM orders WHERE deleted_at < ? AND deleted_at IS NOT NULL",
        (cutoff_date,)
    )
    
    for order in orders_to_purge:
        # Backup
        backup_storage.store(
            path=f"purged-orders/{now().year}/{order.id}.json",
            content=json.dumps(order)
        )
        
        # Borrar
        db.execute("DELETE FROM orders WHERE id = ?", (order.id,))
        
        # Log inmutable
        immutable_log.append({
            "action": "purged_order",
            "order_id": order.id,
            "purged_at": now(),
            "backup_location": f"s3://backup/purged-orders/{order.id}",
        })
```

---

## 3) Autorización (quién puede ver/cambiar qué)

### Roles base
```python
class Role(Enum):
    CUSTOMER = "customer"      # Ve solo sus propios datos
    OPERATOR = "operator"      # Ve datos operacionales (carriers, rutas)
    ADMIN = "admin"            # Ve/modifica todo
    AUDITOR = "auditor"        # Solo lectura, logs y auditoría
```

### Implementación
```python
def requires_role(*allowed_roles):
    """Decorator: verifica role antes de permitir acceso"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                logger.warn(
                    "Unauthorized access attempt",
                    extra={
                        "user_id": request.user.id,
                        "role": request.user.role,
                        "endpoint": request.url.path,
                        "ip": request.client.host
                    }
                )
                return JSONResponse(status_code=403, content={"code": "FORBIDDEN"})
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.get("/v1/admin/audit-logs")
@requires_role(Role.ADMIN, Role.AUDITOR)
async def view_audit_logs(request: Request):
    """Solo admin y auditor pueden ver logs"""
    # ...
```

---

## 4) Encriptación

### En tránsito (HTTPS siempre)
```nginx
# En nginx/load balancer
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!eNULL;
}
```

### En reposo (para datos Restricted+)
```python
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY")  # Rotated anually
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_pii(data: str) -> str:
    return cipher.encrypt(data.encode()).decode()

def decrypt_pii(encrypted_data: str) -> str:
    return cipher.decrypt(encrypted_data.encode()).decode()

# En BD schema
class Customer(Base):
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)  # Public
    phone = Column(String, nullable=False)  # Public (hashed, no plaintext)
    
    # Encrypted: solo admin puede ver
    _address_encrypted = Column(LargeBinary, nullable=True)
    
    @property
    def address(self):
        if self._address_encrypted:
            return decrypt_pii(self._address_encrypted)
        return None
    
    @address.setter
    def address(self, value):
        if value:
            self._address_encrypted = encrypt_pii(value)
```

---

## 5) Auditoría y cumplimiento

### Tabla de auditoría (inmutable)
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100),           -- "create_order", "list_orders", "delete_order"
    object_type VARCHAR(50),       -- "order", "customer", "rate"
    object_id VARCHAR(100),
    user_id VARCHAR(100),
    
    -- En caso de cambio: antes/después
    old_values JSONB,
    new_values JSONB,
    
    timestamp TIMESTAMP,
    ip_address VARCHAR(50),
    
    -- Anti-tampering
    hash_previous_row CHAR(64),    -- SHA256 de fila anterior
    
    CONSTRAINT no_update_delete CHECK (1=1)  -- Trigger previene UPDATE/DELETE
);
```

### Query para investigar
```sql
-- ¿Quién accedió a qué?
SELECT user_id, action, timestamp FROM audit_log 
WHERE object_id = 'O-123' 
ORDER BY timestamp DESC
LIMIT 100;

-- ¿Qué cambió en una orden?
SELECT user_id, old_values, new_values, timestamp FROM audit_log
WHERE object_id = 'O-123' AND action = 'update_order'
ORDER BY timestamp DESC;

-- ¿Quién borró datos?
SELECT user_id, object_id, timestamp FROM audit_log
WHERE action = 'delete_order'
AND timestamp > now() - interval '30 days';
```

---

## 6) Incidente: qué hacer si hay leak

1. **Contener:**
   - Stop new writes a data affected.
   - Notificar a CTO inmediatamente.
   - Preserve logs (no borrar nada).

2. **Investigar:**
   ```bash
   # Auditoría: quién tuvo acceso
   grep -i "unauthorized\|suspicious" audit.log | tail -1000
   
   # Logs de aplicación
   grep "export\|download\|leak" app.log
   ```

3. **Comunicar:**
   - Notify users affected (si PII).
   - Detailed RCA (root cause analysis).
   - Remediation plan.

4. **Prevenir futuro:**
   - Crear ADR si falta control.
   - Actualizar esta policy.
   - Test incident response regularly.

---

## Checklist: antes de ir a producción

- [ ] ¿Datos clasificados por sensibilidad?
- [ ] ¿Soft-delete implementado?
- [ ] ¿Auditoría log en lugar?
- [ ] ¿RBAC (role-based access control) funcional?
- [ ] ¿Encriptación en tránsito (HTTPS)?
- [ ] ¿Encriptación en reposo? (si Restricted+)
- [ ] ¿Backup diario?
- [ ] ¿Data retention policy documentada?
- [ ] ¿Incident response plan (leak/corruption)?
- [ ] ¿Personal security trained (not storing pwd in code)?
