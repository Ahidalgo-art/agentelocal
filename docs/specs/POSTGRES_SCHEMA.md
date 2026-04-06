# SPEC — PostgreSQL schema operativo

## 1. Objetivo

Definir la persistencia específica del proyecto para soportar:
- sincronización incremental;
- shortlist de hilos;
- propuestas de borradores;
- aprobaciones;
- auditoría;
- recuperación operacional.

## 2. Principios del modelo

1. Separar **payload externo** de **estado de dominio**.
2. Priorizar **idempotencia** y **reprocesado seguro**.
3. Evitar joins innecesarios en consultas calientes.
4. Permitir purga selectiva sin romper trazabilidad mínima.
5. Registrar cursores de sync y ejecuciones operativas.

## 3. Esquema lógico

## 3.1 `workspace_account`

Representa la cuenta conectada a Google.

Campos propuestos:
- `id` UUID PK
- `provider` TEXT NOT NULL default `google`
- `external_account_email` TEXT NOT NULL UNIQUE
- `display_name` TEXT NULL
- `is_active` BOOLEAN NOT NULL default true
- `oauth_subject` TEXT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Índices:
- unique sobre `external_account_email`

## 3.2 `oauth_credential_ref`

Referencia a credenciales/tokens sin obligar a guardar secretos en claro.

Campos:
- `id` UUID PK
- `account_id` UUID FK -> `workspace_account.id`
- `storage_mode` TEXT NOT NULL  -- db_encrypted | keyring_ref | file_ref
- `encrypted_refresh_token` BYTEA NULL
- `encrypted_access_token` BYTEA NULL
- `token_expiry_at` TIMESTAMPTZ NULL
- `scopes_hash` TEXT NOT NULL
- `status` TEXT NOT NULL  -- valid | revoked | expired | reauth_required
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Índices:
- index por `account_id`
- index por `status`

## 3.3 `gmail_thread`

Agregado principal de conversación.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `gmail_thread_id` TEXT NOT NULL
- `subject_normalized` TEXT NULL
- `last_message_at` TIMESTAMPTZ NULL
- `message_count` INTEGER NOT NULL default 0
- `participants_cache` JSONB NOT NULL default '[]'
- `labels_cache` JSONB NOT NULL default '[]'
- `has_unread` BOOLEAN NOT NULL default false
- `is_starred` BOOLEAN NOT NULL default false
- `is_important_label` BOOLEAN NOT NULL default false
- `last_history_id` TEXT NULL
- `agent_state` TEXT NOT NULL default 'discovered'
- `requires_response` BOOLEAN NULL
- `last_triaged_at` TIMESTAMPTZ NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`account_id`, `gmail_thread_id`)

Índices:
- (`account_id`, `last_message_at` desc)
- (`account_id`, `agent_state`)
- (`account_id`, `has_unread`, `last_message_at` desc)
- GIN opcional en `participants_cache`

## 3.4 `gmail_message`

Representa mensaje individual del hilo.

Campos:
- `id` UUID PK
- `thread_id` UUID FK -> `gmail_thread.id`
- `gmail_message_id` TEXT NOT NULL
- `gmail_internal_date_at` TIMESTAMPTZ NULL
- `sender_email` TEXT NULL
- `recipient_to` JSONB NOT NULL default '[]'
- `recipient_cc` JSONB NOT NULL default '[]'
- `message_id_header` TEXT NULL
- `in_reply_to_header` TEXT NULL
- `references_header` TEXT NULL
- `snippet` TEXT NULL
- `body_text` TEXT NULL
- `body_html` TEXT NULL
- `headers_json` JSONB NOT NULL default '{}'
- `label_ids_json` JSONB NOT NULL default '[]'
- `payload_hash` TEXT NULL
- `is_inbound` BOOLEAN NOT NULL
- `is_latest_in_thread` BOOLEAN NOT NULL default false
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`thread_id`, `gmail_message_id`)

Índices:
- (`thread_id`, `gmail_internal_date_at`)
- (`thread_id`, `is_latest_in_thread`)
- (`sender_email`)

## 3.5 `gmail_label_snapshot`

Snapshot operativo de labels observados.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `gmail_label_id` TEXT NOT NULL
- `name` TEXT NOT NULL
- `type` TEXT NOT NULL
- `label_list_visibility` TEXT NULL
- `message_list_visibility` TEXT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`account_id`, `gmail_label_id`)

## 3.6 `calendar_source`

Calendario visible por la cuenta.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `google_calendar_id` TEXT NOT NULL
- `summary` TEXT NULL
- `primary_flag` BOOLEAN NOT NULL default false
- `selected_flag` BOOLEAN NOT NULL default true
- `timezone` TEXT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`account_id`, `google_calendar_id`)

## 3.7 `calendar_event`

Evento sincronizado para contexto.

Campos:
- `id` UUID PK
- `calendar_source_id` UUID FK -> `calendar_source.id`
- `google_event_id` TEXT NOT NULL
- `status` TEXT NOT NULL
- `summary` TEXT NULL
- `description` TEXT NULL
- `organizer_email` TEXT NULL
- `attendees_json` JSONB NOT NULL default '[]'
- `starts_at` TIMESTAMPTZ NULL
- `ends_at` TIMESTAMPTZ NULL
- `all_day` BOOLEAN NOT NULL default false
- `location` TEXT NULL
- `meet_link` TEXT NULL
- `etag` TEXT NULL
- `updated_remote_at` TIMESTAMPTZ NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`calendar_source_id`, `google_event_id`)

Índices:
- (`calendar_source_id`, `starts_at`)
- (`calendar_source_id`, `updated_remote_at`)
- GIN opcional en `attendees_json`

## 3.8 `sync_cursor`

Cursores por recurso y cuenta.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `resource_type` TEXT NOT NULL  -- gmail_history | calendar_sync
- `resource_key` TEXT NOT NULL   -- inbox/global/calendar_id
- `cursor_value` TEXT NULL
- `cursor_status` TEXT NOT NULL  -- valid | stale | requires_full_resync
- `last_synced_at` TIMESTAMPTZ NULL
- `last_successful_run_id` UUID NULL
- `updated_at` TIMESTAMPTZ NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`account_id`, `resource_type`, `resource_key`)

## 3.9 `sync_run`

Registro de ejecuciones de sync.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `resource_type` TEXT NOT NULL
- `resource_key` TEXT NOT NULL
- `mode` TEXT NOT NULL  -- incremental | full
- `status` TEXT NOT NULL  -- running | succeeded | partial | failed
- `started_at` TIMESTAMPTZ NOT NULL
- `finished_at` TIMESTAMPTZ NULL
- `items_seen` INTEGER NOT NULL default 0
- `items_upserted` INTEGER NOT NULL default 0
- `items_deleted` INTEGER NOT NULL default 0
- `error_code` TEXT NULL
- `error_message` TEXT NULL
- `meta_json` JSONB NOT NULL default '{}'

Índices:
- (`account_id`, `resource_type`, `started_at` desc)
- (`status`, `started_at` desc)

## 3.10 `triage_decision`

Resultado de priorización por hilo y ejecución.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `thread_id` UUID FK -> `gmail_thread.id`
- `decision_version` TEXT NOT NULL
- `importance_score` NUMERIC(5,4) NOT NULL
- `confidence_score` NUMERIC(5,4) NOT NULL
- `requires_response` BOOLEAN NOT NULL
- `priority_bucket` TEXT NOT NULL  -- critical | high | medium | low | fyi
- `reasons_json` JSONB NOT NULL default '[]'
- `signals_json` JSONB NOT NULL default '{}'
- `calendar_context_json` JSONB NOT NULL default '{}'
- `decided_at` TIMESTAMPTZ NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL

Índices:
- (`thread_id`, `decided_at` desc)
- (`account_id`, `priority_bucket`, `decided_at` desc)

## 3.11 `draft_suggestion`

Propuesta estructurada y texto de borrador.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `thread_id` UUID FK
- `triage_decision_id` UUID FK
- `status` TEXT NOT NULL  -- proposed | approved | rejected | superseded | draft_created
- `intent` TEXT NOT NULL  -- acknowledge | ask_clarification | propose_slots | commit | decline | custom
- `model_name` TEXT NULL
- `prompt_version` TEXT NOT NULL
- `input_context_hash` TEXT NOT NULL
- `summary_for_user` TEXT NOT NULL
- `why_this_reply` TEXT NOT NULL
- `missing_information_json` JSONB NOT NULL default '[]'
- `draft_subject` TEXT NULL
- `draft_body_text` TEXT NOT NULL
- `draft_body_html` TEXT NULL
- `confidence_score` NUMERIC(5,4) NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL
- `updated_at` TIMESTAMPTZ NOT NULL

Índices:
- (`thread_id`, `created_at` desc)
- (`status`, `created_at` desc)
- (`triage_decision_id`)

## 3.12 `approval_decision`

Acción humana sobre propuesta.

Campos:
- `id` UUID PK
- `draft_suggestion_id` UUID FK
- `decision` TEXT NOT NULL  -- approve | reject | edit_then_approve | snooze
- `edited_body_text` TEXT NULL
- `edited_body_html` TEXT NULL
- `comment` TEXT NULL
- `decided_by` TEXT NOT NULL
- `decided_at` TIMESTAMPTZ NOT NULL
- `created_at` TIMESTAMPTZ NOT NULL

Índices:
- (`draft_suggestion_id`, `decided_at` desc)

## 3.13 `gmail_draft_binding`

Vincula propuesta local con draft remoto.

Campos:
- `id` UUID PK
- `draft_suggestion_id` UUID FK
- `gmail_draft_id` TEXT NOT NULL
- `gmail_message_id` TEXT NULL
- `created_remote_at` TIMESTAMPTZ NOT NULL
- `last_seen_status` TEXT NOT NULL default 'created'
- `created_at` TIMESTAMPTZ NOT NULL

Restricciones:
- unique (`draft_suggestion_id`)
- unique (`gmail_draft_id`)

## 3.14 `audit_event`

Registro inmutable de eventos críticos.

Campos:
- `id` UUID PK
- `account_id` UUID FK
- `aggregate_type` TEXT NOT NULL
- `aggregate_id` UUID NULL
- `event_type` TEXT NOT NULL
- `trace_id` TEXT NOT NULL
- `actor_type` TEXT NOT NULL  -- system | human | agent
- `actor_id` TEXT NULL
- `payload_json` JSONB NOT NULL default '{}'
- `occurred_at` TIMESTAMPTZ NOT NULL

Índices:
- (`account_id`, `occurred_at` desc)
- (`aggregate_type`, `aggregate_id`, `occurred_at` desc)
- (`trace_id`)

## 4. Consultas calientes esperadas

1. shortlist de hilos pendientes por importancia y recencia;
2. último triage de un hilo;
3. última propuesta de draft por hilo;
4. eventos de agenda en ventana temporal próxima;
5. últimas ejecuciones de sync fallidas;
6. borradores aprobados pendientes de creación remota.

## 5. Estrategias de partición y retención

### Recomendación inicial

Sin partición física al inicio.

### Cuándo introducir partición

- `audit_event` con alto volumen;
- `sync_run` histórico muy grande;
- `gmail_message` si se persiste cuerpo completo de forma masiva.

### Retención sugerida

- `sync_run`: 90–180 días
- `audit_event`: 180–365 días mínimo
- `gmail_message.body_html/body_text`: política configurable de purga selectiva
- `draft_suggestion`: retención larga por valor de aprendizaje

## 6. Recomendaciones transaccionales

- Upsert por claves externas naturales.
- Cursor y resultado de sync en la misma transacción lógica si el proceso es atómico.
- `approval_decision` + actualización de `draft_suggestion.status` en una única transacción.
- `gmail_draft_binding` solo tras confirmación remota de creación de draft.

## 7. Constraints de integridad funcional

- un `draft_suggestion` en `draft_created` debe tener un `gmail_draft_binding` asociado;
- una `approval_decision` con `approve` o `edit_then_approve` es precondición para `gmail_draft_binding`;
- un `sync_cursor` en `requires_full_resync` bloquea incremental hasta cierre explícito del run de resync.
