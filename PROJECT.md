# PROJECT — Reinicio rápido

## 1) Estado global
- Estado: `BOOTSTRAP` (proyecto recién inicializado).
- Sprint activo: `Sprint 0`.
- Objetivo inmediato: establecer baseline técnico y operativo.

## 2) Próximos pasos (orden recomendado)
1. Definir ADR de arquitectura base (`docs/adr/ADR-0001-arquitectura-base.md`).
2. Crear esqueleto backend hexagonal y endpoint `GET /v1/health`.
3. Configurar CI mínimo (`lint + tests + security + smoke`).
4. Definir política de secretos/config por entorno.

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
- Próximo paso: iniciar la primera feature de negocio del Sprint 1 (`POST /v1/rates/import`) manteniendo patrón hexagonal.
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
