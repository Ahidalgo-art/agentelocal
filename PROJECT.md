# PROJECT — Reinicio rápido

## 1) Estado global
- Estado: `BOOTSTRAP` (proyecto recién inicializado).
- Sprint activo: `Sprint 1`.
- Objetivo inmediato: avanzar la capability de correo+calendar según `PROJECT_CORREO_AGENT.md`.

## 2) Próximos pasos (orden recomendado)
1. Implementar sync Gmail incremental con persistencia de estado (`sync_cursor` + `sync_run`).
2. Implementar sync Calendar incremental y recuperación controlada.
3. Consolidar shortlist de hilos importantes con trazabilidad de decisión.
4. Mantener human-in-the-loop para propuestas y creación de drafts.

## 3) Bloqueos actuales
- Ninguno registrado.

## 4) Comandos sanity check (actualizar al crear código)
```powershell
# Install
cd backend
python -m pip install -e .

# Lint
ruff check src tests

# Tests
$env:PYTHONPATH='src'; pytest -q

# Run
python -m uvicorn <app>.main:app --host 127.0.0.1 --port 8000

# Health
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/health | ConvertTo-Json -Depth 5
```

## 5) Fuente canónica por tema
- Arquitectura: `.github/copilot-instructions.md`
- Gobierno de ejecución: `AGENTS.md`
- Gobernanza (roles + SLA + políticas): `GOVERNANCE.md`
- Estado del proyecto: `PROJECT.md`
- Decisiones técnicas: `docs/adr/`
- Onboarding rápido: `QUICKSTART.md`
- Runbooks operacionales: `docs/runbooks/`

## 6) Bitácora de pausa/reinicio
### 2026-04-06 — Cierre formal Sprint 0 (GO)
- Estado al pausar: Sprint 0 cerrado en `GO` con baseline técnico/operativo, repositorio publicado y CI remoto en verde.
- Completado:
	- Git inicializado y remoto configurado en `https://github.com/Ahidalgo-art/agentelocal.git`.
	- Pipeline `Backend CI` ajustado para estructura real + servicio PostgreSQL en migraciones.
	- Política de secretos/config por entorno cerrada con `.gitignore` + `backend/.env.example` + runbook operativo.
	- Dependencia `psycopg[binary]` añadida para compatibilidad de migraciones en CI.
- Evidencia verificable:
	- Commit de cierre técnico: `2520da6a290f4db39bd4f6b571668a4cd4c90de2`.
	- Run exitoso de CI: `https://github.com/Ahidalgo-art/agentelocal/actions/runs/24030561185` (`quality-security-gates: success`).
- Próximo paso: avanzar capability de correo/calendar definida en `PROJECT_CORREO_AGENT.md` y `docs/specs/SPEC_CORREO_CALENDAR_AGENT_LOCAL.md`.
- Riesgos/deuda residual: ninguno crítico para arranque de Sprint 1.

### 2026-04-06 — Cierre de política de secretos/config por entorno
- Estado al pausar: se cerró el baseline operativo de secretos y configuración por entorno con artefactos y checklist verificable.
- Próximo paso: validar la ejecución real del workflow en GitHub Actions tras push para cerrar el riesgo residual del pipeline.
- Riesgos: existe `.env` local con credenciales en entorno de desarrollo; mantener fuera de control de versiones y rotar si hubo exposición previa.

### 2026-04-06 — Alineación de CI con estructura real
- Estado al pausar: el backend hexagonal y `GET /v1/health` ya estaban operativos; se corrigió el pipeline para apuntar a rutas reales del repositorio.
- Próximo paso: cerrar y validar la política de secretos/configuración por entorno como baseline operativo.
- Riesgos: no hay bloqueos críticos; pendiente verificar ejecución del workflow en GitHub Actions tras push.

### 2026-03-18 — Inicio de plantilla
- Estado al pausar: baseline documental creado.
- Próximo paso: implementar esqueleto backend y CI.
- Riesgos: ninguno crítico.

## Bitácora — 2026-04-06
- **Completado:** Git inicializado y repo publicado en `https://github.com/Ahidalgo-art/agentelocal.git`; CI corregido en `.github/workflows/backend_ci.yml` (rutas + PostgreSQL service para migraciones); baseline de secretos/config cerrado (`.gitignore`, `backend/.env.example`, runbook) y `Backend CI` en verde.
- **En proceso:** Ninguno; lo ejecutado hoy quedó `DONE` según AGENTS.md con evidencia en commits y Actions.
- **Próxima sesión:** Implementar siguiente incremento de correo/calendar en `backend/src/agente_local/application/ports/` + `backend/src/agente_local/infrastructure/` para sync incremental, con tests en `backend/tests/` sin romper contratos actuales.
- **Riesgos / deuda:** Evitar desvíos a ejemplos de plantilla; el alcance válido para este repo está en `PROJECT_CORREO_AGENT.md` y `docs/specs/SPEC_CORREO_CALENDAR_AGENT_LOCAL.md`.

## Bitácora — 2026-04-06 (continuación)
- **Completado:** se consolidó el flujo de sync workspace con endpoint `POST /v1/sync/{account_id}`, persistencia de `calendar_source` + `calendar_event`, y validación explícita de configuración Google por entorno sin hardcode.
- **Completado:** se eliminó `.env` duplicado en raíz y se estableció `backend/.env` como fuente única local; `backend/.env.example` y `QUICKSTART.md` quedaron actualizados con variables Google requeridas.
- **Completado:** recuperación controlada en Calendar ante expiración de `sync_token` (HTTP 410): se marca cursor `stale` y se ejecuta re-sync sin token para ese calendario.
- **Verificación:** `ruff check` en archivos modificados y `pytest -q` completo en verde (52 passed, cobertura 84.31%).
- **En proceso:** ninguno abierto.
- **Próxima sesión:** aplicar el mismo patrón de degradación controlada para Gmail history invalidado y registrar `sync_run` con estado `partial/needs_full_resync` cuando corresponda.
- **Riesgos / deuda:** persisten cambios autogenerados en `backend/src/nuevo_proyecto_backend.egg-info/` fuera del alcance funcional; no se incluyen en commit limpio.
