# Contratos de herramientas / puertos

## 1. Objetivo

Definir los puertos de aplicación que necesita el orquestador para operar sin acoplarse a APIs externas ni a detalles de PostgreSQL.

## 2. Puertos de entrada (use cases)

### `SyncWorkspaceUseCase`

Responsabilidad:
- lanzar sync Gmail + Calendar para una cuenta.

Input:
- `account_id`
- `mode` (`incremental|full`)
- `resource_scope` (`gmail|calendar|all`)

Output:
- resumen de ejecución con contadores y estados.

### `GetImportantThreadsUseCase`

Responsabilidad:
- obtener shortlist priorizado.

Input:
- `account_id`
- `limit`
- `window_hours`
- filtros opcionales

Output:
- lista de hilos con último triage.

### `GenerateDraftSuggestionUseCase`

Responsabilidad:
- producir propuesta de borrador para un hilo.

Input:
- `account_id`
- `thread_id`
- `regeneration_reason` opcional

Output:
- `draft_suggestion`

### `ApproveDraftSuggestionUseCase`

Responsabilidad:
- registrar decisión humana.

Input:
- `draft_suggestion_id`
- `decision`
- texto editado opcional
- comentario opcional

Output:
- propuesta actualizada

### `CreateRemoteDraftUseCase`

Responsabilidad:
- materializar en Gmail un draft aprobado.

Input:
- `draft_suggestion_id`

Output:
- binding remoto creado

## 3. Puertos de salida — Integración Google

### `GmailReadPort`

Operaciones:
- `list_candidate_threads(account_ref, query, page_token)`
- `get_thread_metadata(account_ref, gmail_thread_id)`
- `get_thread_full(account_ref, gmail_thread_id)`
- `list_history(account_ref, start_history_id)`
- `list_labels(account_ref)`

### `GmailDraftPort`

Operaciones:
- `create_draft(account_ref, thread_context, mime_message)`
- `get_draft(account_ref, gmail_draft_id)`

### `CalendarReadPort`

Operaciones:
- `list_calendars(account_ref)`
- `list_events(account_ref, calendar_id, sync_token, time_min, time_max)`
- `compute_availability(account_ref, window)`

### `OAuthPort`

Operaciones:
- `load_valid_credentials(account_id)`
- `refresh_credentials(account_id)`
- `mark_reauth_required(account_id, reason)`

## 4. Puertos de salida — Persistencia

### `WorkspaceRepository`

Operaciones:
- upsert cuentas
- upsert hilos
- upsert mensajes
- upsert labels
- upsert calendarios
- upsert eventos
- obtener shortlist base

### `SyncRepository`

Operaciones:
- leer/escribir cursores
- crear `sync_run`
- cerrar `sync_run`
- marcar cursor stale

### `TriageRepository`

Operaciones:
- persistir decisión
- obtener última decisión por hilo
- listar candidatos sin triage vigente

### `DraftRepository`

Operaciones:
- crear propuesta
- actualizar estado
- registrar aprobación
- crear binding remoto
- obtener última propuesta por hilo

### `AuditRepository`

Operaciones:
- append-only de eventos críticos

## 5. Puertos de salida — Inteligencia

### `ImportanceScoringPort`

Input:
- metadata de hilo
- señales calculadas
- contexto local

Output:
- score
- bucket
- razones
- confianza

### `DraftGenerationPort`

Input:
- contexto de hilo
- contexto temporal
- preferencias de tono
- intención objetivo

Output:
- resumen
- borrador
- faltantes
- confianza

## 6. Reglas contractuales

- Ningún puerto devuelve objetos de infraestructura crudos fuera de su boundary.
- Toda operación que tenga efectos externos debe devolver identificadores remotos normalizados.
- Toda excepción externa debe traducirse a un error de dominio/aplicación controlado.
- Los puertos no deben mezclar IO externo con decisiones de negocio.
