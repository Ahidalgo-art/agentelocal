# ADR-011 — PostgreSQL como store operacional y de auditoría

- **Estado:** Aprobado
- **Fecha:** 2026-04-05

## Contexto

El proyecto necesita persistir entidades de dominio, payloads normalizados, cursores de sincronización, decisiones del agente, aprobaciones humanas y trazas de auditoría. El usuario dispone de una instancia local de PostgreSQL.

## Decisión

Se adopta PostgreSQL como almacenamiento principal para:
- estado operativo del workspace sincronizado;
- cursores de sync;
- shortlist y decisiones de triage;
- propuestas de drafts;
- aprobaciones;
- auditoría.

## Justificación

- ACID y transaccionalidad adecuadas para sync + cambios de estado.
- JSONB para caches y payloads semi-estructurados.
- Buen encaje con repositorios hexagonales.
- Capacidad suficiente para una instancia local single-user.

## Consecuencias

### Positivas

- Modelo único de verdad local.
- Consultas ricas para shortlist, replay y observabilidad.
- Menor complejidad que introducir varios stores desde el inicio.

### Negativas

- Riesgo de sobrecargar la BD si se persiste HTML bruto masivamente.
- Necesidad de políticas de retención y purga.

## Alternativas descartadas

### A. SQLite

Descartado porque existe PostgreSQL local disponible y se valora más la robustez operativa y capacidades SQL/JSONB.

### B. Postgres + vector DB desde el día 1

Descartado por sobreingeniería prematura. La necesidad de retrieval semántico avanzado se revaluará más adelante.
