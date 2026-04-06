# DESIGN-03: Nuevas dependencias — P0 del proyecto

**Estado:** 🔵 En propuesta (GATE: requiere aprobación Lead Tech + VP Engr)  
**Fecha:** 2026-04-05  
**Impacto:** 🟡 Medio — Introducen 3 nuevas dependencias (Google, encoding, serialization)

---

## 1. Objetivo

Especificar versiones y configuración de paquetes necesarios para:
- Autenticación OAuth2 con Google
- Lectura de Gmail + Calendar APIs
- Serialización JSON + encoding
- Performance en aplicaciones async

**Constraint:** Minimizar dependencias (sin bloat).

---

## 2. Nuevas dependencias propuestas

### Grupo A: Google APIs (CRÍTICAS)

#### A1. `google-auth`

```toml
google-auth = ">=2.27.0,<3.0.0"
```

**Propósito:** OAuth2 refresh tokens, validación de JWT  
**Versión:** 2.27+ (stable, sin breaking changes recientes)  
**Tamaño:** ~300KB  
**Riesgo de ruptura:** Bajo (estable desde 2020)  
**Alternativa:** ninguna (oficial de Google)

**En `pyproject.toml`:**
```toml
dependencies = [
    # ... existentes
    "google-auth>=2.27.0,<3.0.0",
]
```

---

#### A2. `google-auth-oauthlib`

```toml
google-auth-oauthlib = ">=1.1.0,<2.0.0"
```

**Propósito:** Flujo OAuth2 local (authorization code grant)  
**Versión:** 1.1+ (compatible con google-auth 2.27+)  
**Tamaño:** ~50KB  
**Integración:** LocalAuthHandler para supervisor local  
**Nota:** Solo en dev/local; en prod será credentials de service account

---

#### A3. `google-api-python-client`

```toml
google-api-python-client = ">=1.23.0,<2.0.0"
```

**Propósito:** Cliente de Gmail + Calendar REST APIs  
**Versión:** 1.23+ (includes async support via httpx)  
**Tamaño:** ~2.5MB (con descarga de esquemas)  
**Performance:** Nativo async si pasamos transport de httpx  
**Riesgo:** Medium (Google actualiza endpoints ocasionalmente)

**Nota:** Incluye descarga de `google_api_library.pickle` en primera ejecución (~500KB).

---

### Grupo B: Serialización y tipos

#### B1. `pydantic-extra-types`

```toml
pydantic-extra-types = ">=2.0.0,<3.0.0"
```

**Propósito:** Tipos adicionales para Pydantic (Email, UUID validado, etc.)  
**Versión:** 2.0+ (compatible con Pydantic 2.8+)  
**Tamaño:** ~50KB  
**Alternativa:** Manual validation (no, extra-types es oficial de Pydantic)

---

#### B2. `python-multipart`

```toml
python-multipart = ">=0.0.7,<0.1.0"
```

**Propósito:** Parsing de formularios multipart (si algún endpoint carga archivos)  
**Versión:** 0.0.7+ (reciente)  
**Tamaño:** ~20KB  
**Riesgo:** Bajo  
**Alternativa:** No (requerido para FastAPI file uploads)

---

### Grupo C: Async + Performance (OPCIONALES pero RECOMENDADOS)

#### C1. `httpx`

```toml
httpx = ">=0.26.0,<1.0.0"
```

**Propósito:** Cliente HTTP async nativo (en lugar de requests + asyncio wrapper)  
**Versión:** 0.26+ (estable async, compatible con google-api-python-client)  
**Tamaño:** ~200KB  
**Ventaja:** Mejor performance en sync runs
→ Permite pasar como transport a google-api-python-client  
**Riesgo:** Bajo (ampliamente usado)

---

#### C2. `orjson`

```toml
orjson = ">=3.9.0,<4.0.0"
```

**Propósito:** Serialización JSON 10x más rápida (alternativa a json.dumps)  
**Versión:** 3.9+ (reciente)  
**Tamaño:** ~100KB  
**Integración:** Con `FastAPI(json_encoder=...)` o manual en responders  
**Riesgo:** Muy bajo (usado ampliamente en FastAPI projects)  
**Alternativa:** Seguir con json built-in (pero lento para grandes payloads)

---

### Grupo D: Testing (DEV only)

```toml
[project.optional-dependencies]
dev = [
  # ... existentes
  "pytest-asyncio>=0.24.0",           # tests async
  "google-auth-stubs>=0.1.0",         # typing hints para google-auth
  "responses>=0.25.0",                # mock de HTTP requests
]
```

---

## 3. Matriz de decisión

| Paquete | Crítico | Recomendado | Bundleado? | SLA actualización |
|---|---|---|---|---|
| google-auth | ✅ SÍ | SÍ | NO (manual) | 12 meses |
| google-auth-oauthlib | ✅ SÍ (local) | SÍ | NO | 12 meses |
| google-api-python-client | ✅ SÍ | SÍ | NO | 12 meses |
| pydantic-extra-types | ⚠️ NO | SÍ | Con Pydantic | 6 meses |
| httpx | ✅ SÍ | SÍ | NO | 6 meses |
| orjson | ⚠️ NO | SÍ (perf) | NO | 6 meses |
| python-multipart | ⚠️ NO | NO | NO | 12 meses |

---

## 4. Impacto en `pyproject.toml`

```toml
[project]
name = "tarifas-transporte"
version = "0.1.0"
description = "Agente local de correo + calendario"
requires-python = ">=3.12"

dependencies = [
  # Existentes
  "fastapi>=0.115.0,<1.0.0",
  "uvicorn[standard]>=0.30.0,<1.0.0",
  "sqlalchemy>=2.0.0,<3.0.0",
  "alembic>=1.13.0,<2.0.0",
  "pydantic>=2.8.0,<3.0.0",
  
  # ⭐ NUEVAS — Google APIs
  "google-auth>=2.27.0,<3.0.0",
  "google-auth-oauthlib>=1.1.0,<2.0.0",
  "google-api-python-client>=1.23.0,<2.0.0",
  
  # ⭐ NUEVAS — Serialización
  "pydantic-extra-types>=2.0.0,<3.0.0",
  "python-multipart>=0.0.7,<0.1.0",
  
  # ⭐ NUEVAS — Performance  
  "httpx>=0.26.0,<1.0.0",
  "orjson>=3.9.0,<4.0.0",
]

[project.optional-dependencies]
dev = [
  # Existentes
  "pytest>=8.0.0",
  "pytest-cov>=5.0.0",
  "pytest-env>=1.1.0",
  "httpx>=0.27.0",  # ya incluido arriba, pero también en dev
  "ruff>=0.4.0",
  "import-linter>=2.0",
  
  # ⭐ NUEVAS — Testing
  "pytest-asyncio>=0.24.0",
  "google-auth-stubs>=0.1.0",
  "responses>=0.25.0",
]
```

---

## 5. Verificación de compatibilidad

### A ejecutar post-instalación:

```bash
# Verificar imports básicos
python -c "
import google.auth
import google.oauth2.service_account
import google.auth.oauthlib.flow
from google.oauth2.credentials import Credentials
import pydantic_extra_types
import httpx
import orjson

print('✅ All imports successful')
"

# Verificar versiones
pip list | grep -E "google-auth|google-api|pydantic|httpx|orjson"
```

---

## 6. Riesgos de integración

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| **google-api-python-client > 2.0 breaking change** | 🟡 Media | Pindown a 1.x; monitorear Google releases |
| **Conflicto de transporte HTTP** | 🟢 Baja | Usar httpx como transport explícito en client init |
| **Tamaño bundle creció 15%** | 🟢 Baja | Aceptable; documentar en runbook |
| **Dependencia transitiva deprecated** | 🟡 Media | Ejecutar `pip-audit` en CI; alert si CVE |

---

## 7. Auditoría de seguridad

```bash
# Post-install
pip-audit

# Expected: Sin HIGH o CRITICAL sin parche disponible
```

---

## 8. Plan de actualización (para futuro)

| Horizonte | Acción |
|---|---|
| **Mensual** | `pip list --outdated`; evaluar minor updates |
| **Trimestral** | `pip-audit`; evaluar nuevas versiones |
| **Semestral** | Revisión completa de google-api-python-client major |

---

## 9. Firma de aprobación

### Para proceder a Implement:

- [ ] Lead Tech aprueba lista de paquetes
- [ ] VP Engr aprueba presupuesto (bundle size, maintenance burden)
- [ ] Revisor verifica criterios de seguridad (§7)

---

## 10. Para la siguiente sesión: Implement

Una vez aprobado, implementaré:
1. ✅ Actualizar `pyproject.toml` con nuevas dependencias
2. ✅ Ejecutar `pip install -e ".[dev]"`
3. ✅ Validar imports sin errores
4. ✅ Ejecutar `pip-audit`
5. ✅ Commit: `deps: add google apis + serialization + performance packages`
