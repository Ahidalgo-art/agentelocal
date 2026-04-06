# Paquete documental — Agente local Gmail + Google Calendar

Este paquete contiene **solo la documentación específica** del proyecto de agente local para Gmail + Google Calendar con persistencia en **PostgreSQL**, sin repetir el scaffolding general del proyecto.

## Objetivo

Definir el alcance, arquitectura específica, modelo de datos, flujo agent-first, decisiones arquitectónicas y runbooks operativos necesarios para implementar un agente supervisado que:

- sincroniza Gmail y Google Calendar en local;
- identifica correos relevantes;
- propone borradores de respuesta;
- crea borradores en Gmail solo tras aprobación explícita;
- persiste estado operativo, auditoría y sincronización incremental en PostgreSQL.

## Documentos incluidos

- `docs/specs/SPEC_CORREO_CALENDAR_AGENT_LOCAL.md`
- `docs/specs/POSTGRES_SCHEMA.md`
- `docs/specs/AGENT_WORKFLOW.md`
- `docs/contracts/TOOL_CONTRACTS.md`
- `docs/adr/ADR-010-google-workspace-local-supervisado.md`
- `docs/adr/ADR-011-postgres-como-store-operacional-y-auditoria.md`
- `docs/adr/ADR-012-human-in-the-loop-para-drafts.md`
- `docs/runbooks/oauth_google_local.md`
- `docs/runbooks/sincronizacion_y_recuperacion.md`
- `docs/runbooks/data_governance_workspace.md`
- `PROJECT_CORREO_AGENT.md`

## Orden recomendado de lectura

1. `SPEC_CORREO_CALENDAR_AGENT_LOCAL.md`
2. `AGENT_WORKFLOW.md`
3. `POSTGRES_SCHEMA.md`
4. ADRs 010–012
5. Runbooks
6. `PROJECT_CORREO_AGENT.md`
