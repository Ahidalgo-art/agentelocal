# PROJECT — Agente local Gmail + Google Calendar

## 1. Objetivo ejecutivo

Disponer de un agente local supervisado que ayude a gestionar correo importante con contexto de agenda, persistiendo estado y trazabilidad en PostgreSQL.

## 2. Resultado esperado de la primera release

- sync Gmail incremental + full recovery
- sync Calendar incremental + full recovery
- shortlist de correos importantes
- propuesta de borrador por hilo
- aprobación humana
- creación de draft en Gmail
- auditoría y métricas mínimas

## 3. Entregables concretos

### E1. Adaptador Gmail lectura
- listar candidatos
- obtener thread metadata/full
- history incremental

### E2. Adaptador Calendar lectura
- listar calendarios
- eventos por ventana y por sync token

### E3. Persistencia PostgreSQL
- migraciones de tablas del proyecto
- repositorios e índices calientes

### E4. Triage
- heurísticas iniciales
- score + razones + bucket

### E5. Drafting
- propuesta estructurada
- generación textual
- storage de sugerencias

### E6. Human approval + draft remoto
- endpoint/comando de aprobación
- endpoint/comando de creación de draft

## 4. Backlog priorizado

### P0 — Fundacional
- [ ] migraciones Postgres del proyecto
- [ ] repositorios base
- [ ] modelo de cursores y sync runs
- [ ] adaptador OAuth

### P1 — Capacidad núcleo
- [ ] sync Gmail inicial
- [ ] sync Gmail incremental
- [ ] sync Calendar inicial
- [ ] sync Calendar incremental
- [ ] shortlist base por reglas

### P2 — Inteligencia útil
- [ ] scoring de importancia explicable
- [ ] enriquecimiento con agenda
- [ ] propuesta de borrador
- [ ] feedback humano persistido

### P3 — Operación completa
- [ ] creación de draft en Gmail
- [ ] runbooks probados
- [ ] métricas y auditoría
- [ ] tests de integración end-to-end locales

## 5. Riesgos abiertos

- calibración de relevancia insuficiente al inicio;
- calidad desigual del borrador según contexto del hilo;
- recuperación de sync no robusta en primeros ciclos;
- scopes/OAuth cambiantes entre entornos.

## 6. Criterio de DONE por capability

Una capability solo se considera DONE si cumple:
- tests relevantes pasando;
- observabilidad mínima instrumentada;
- runbook actualizado si aplica;
- evidencia operativa reproducible;
- sin estados imposibles en BD.

## 7. Siguientes pasos recomendados

1. convertir `POSTGRES_SCHEMA.md` en migraciones reales;
2. fijar contratos de puertos en código;
3. implementar sync Gmail/Calendar con `sync_run` y `sync_cursor`;
4. montar primer shortlist determinista antes de meter LLM;
5. añadir drafting y aprobación.
