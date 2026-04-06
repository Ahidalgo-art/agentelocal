# CHANGELOG — Plantilla "AgenteLocal"

> Registro de versiones de la plantilla base.  
> Cada proyecto derivado debe registrar en su `PROJECT.md` la versión que usó al crearse.

---

## v1.1.0 — 2026-03-18

### Añadido
- `GOVERNANCE.md` sección 11: Branching strategy (`main`, `develop`, `feature/`, `hotfix/`)
- `GOVERNANCE.md` sección 12: Proceso técnico de aprobación con backups por rol
- `CHANGELOG.md` (este archivo) — versionado de la plantilla
- `.github/copilot-instructions.md` — Política de idioma explícita (Español/Inglés por contexto)
- `.github/dependabot.yml` — Renovación automática semanal de dependencias Python
- `QUICKSTART.md` sección 0: Prerequisitos con comprobación de versiones
- `backend/pyproject.toml` — Threshold de cobertura de tests al 80% (`--cov-fail-under=80`)

### Contexto
Mejoras acordadas en revisión conjunta de metodología (ver `docs/PROPUESTAS_DE_MEJORA.md` Sprint 1).

---

## v1.0.0 — 2026-03-18

### Added (versión inicial)
- Estructura hexagonal base: `domain/`, `application/`, `infrastructure/`, `entrypoints/`
- `GOVERNANCE.md` — RACI, SLA, política Copilot, versionado contratos, observabilidad, degradación
- `AGENTS.md` — Flujo Understand → Implement → Verify, gates de aprobación
- `QUICKSTART.md` — Onboarding 5 minutos
- `PROJECT.md` — Estado ejecutivo del proyecto
- `INSTRUCCIONES_INICIO_PROYECTO.md` v3.0 — Guía de inicio desde plantilla
- `docs/runbooks/operacion_local.md`
- `docs/runbooks/politica_secretos_configuracion.md`
- `docs/runbooks/degradacion_controlada.md`
- `docs/runbooks/observabilidad_checklist.md`
- `docs/runbooks/data_governance.md`
- `docs/adr/ADR-0001-arquitectura-base.md`
- CI: lint (ruff) + tests (pytest) + security (pip-audit)
- FastAPI + SQLAlchemy + Alembic + Pydantic
- Health endpoint `GET /v1/health`

---

## Cómo registrar la versión en un proyecto derivado

En el `PROJECT.md` del proyecto nuevo, añadir:

```markdown
## Plantilla base

- Versión: v1.1.0 (2026-03-18)
- Mejoras posteriores: ver `AgenteLocal/CHANGELOG.md`
```

## Cómo actualizar esta plantilla

1. Implementar el cambio en `AgenteLocal/`.
2. Añadir entrada en este `CHANGELOG.md` con la nueva versión.
3. Si el cambio afecta a proyectos existentes: notificar a los equipos.
4. Versioning: `MAJOR.MINOR.PATCH` (semver informal):
   - MAJOR: cambio incompatible de estructura (rompe proyectos derivados).
   - MINOR: nueva funcionalidad retrocompatible.
   - PATCH: fix, documentación, ajuste menor.
