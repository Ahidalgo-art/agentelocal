# DESIGN-02: Migraciones de schema — 14 tablas P0

**Estado:** 🔵 En propuesta (GATE: requiere aprobación Lead Tech + DBA)  
**Fecha:** 2026-04-05  
**Impacto:** 🔴 Crítico — Define almacenamiento permanente y recuperación

---

## 1. Objetivo

Convertir especificación [POSTGRES_SCHEMA.md](../specs/POSTGRES_SCHEMA.md) en **script de Alembic reversible** que:
- Crea 14 tablas con índices y restricciones
- Soporta rollback seguro (downgrade -1)
- Define foreign keys explícitas para integridad referencial
- Establece políticas de auditoría mínimas

**Scope:** Solo P0 (tablas fundamentales para sincronización y triage).

---

## 2. Tablas P0 (en orden de creación)

> **Dependencias:** account → credentials → threads → messages → ... → draft_suggestions → approvals

### Tabla 1: `workspace_account`

```python
# Almacena conexión de cuenta
id: UUID PK
provider: VARCHAR(32) NOT NULL DEFAULT 'google'
external_account_email: VARCHAR(255) NOT NULL UNIQUE
display_name: VARCHAR(255)
is_active: BOOLEAN NOT NULL DEFAULT true
oauth_subject: VARCHAR(255)
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- UNIQUE `external_account_email`

---

### Tabla 2: `oauth_credential_ref`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
storage_mode: VARCHAR(32) NOT NULL  # 'db_encrypted' | 'keyring_ref' | 'file_ref'
encrypted_refresh_token: BYTEA
encrypted_access_token: BYTEA
token_expiry_at: TIMESTAMPTZ
scopes_hash: VARCHAR(255) NOT NULL
status: VARCHAR(32) NOT NULL  # 'valid' | 'revoked' | 'expired' | 'reauth_required'
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- FK `account_id`
- BTREE `(account_id, status)`

---

### Tabla 3: `gmail_thread`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
gmail_thread_id: VARCHAR(64) NOT NULL
subject_normalized: TEXT
last_message_at: TIMESTAMPTZ
message_count: INTEGER NOT NULL DEFAULT 0
participants_cache: JSONB NOT NULL DEFAULT '[]'::jsonb
labels_cache: JSONB NOT NULL DEFAULT '[]'::jsonb
has_unread: BOOLEAN NOT NULL DEFAULT false
is_starred: BOOLEAN NOT NULL DEFAULT false
is_important_label: BOOLEAN NOT NULL DEFAULT false
last_history_id: VARCHAR(255)
agent_state: VARCHAR(32) NOT NULL DEFAULT 'discovered'
requires_response: BOOLEAN
last_triaged_at: TIMESTAMPTZ
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(account_id, gmail_thread_id)`

**Índices:**
- PK `id`
- BTREE `(account_id, last_message_at DESC)`
- BTREE `(account_id, agent_state)`
- BTREE `(account_id, has_unread, last_message_at DESC)`
- GIN `participants_cache`

---

### Tabla 4: `gmail_message`

```python
id: UUID PK
thread_id: UUID FK -> gmail_thread.id (ON DELETE CASCADE)
gmail_message_id: VARCHAR(64) NOT NULL
gmail_internal_date_at: TIMESTAMPTZ
sender_email: VARCHAR(255)
recipient_to: JSONB NOT NULL DEFAULT '[]'::jsonb
recipient_cc: JSONB NOT NULL DEFAULT '[]'::jsonb
message_id_header: VARCHAR(255)
in_reply_to_header: VARCHAR(255)
references_header: TEXT
snippet: TEXT
body_text: TEXT
body_html: TEXT
headers_json: JSONB NOT NULL DEFAULT '{}'::jsonb
label_ids_json: JSONB NOT NULL DEFAULT '[]'::jsonb
payload_hash: VARCHAR(64)
is_inbound: BOOLEAN NOT NULL
is_latest_in_thread: BOOLEAN NOT NULL DEFAULT false
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(thread_id, gmail_message_id)`

**Índices:**
- PK `id`
- BTREE `(thread_id, gmail_internal_date_at)`
- BTREE `(thread_id, is_latest_in_thread)`
- BTREE `sender_email`

---

### Tabla 5: `gmail_label_snapshot`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
gmail_label_id: VARCHAR(64) NOT NULL
name: VARCHAR(255) NOT NULL
type: VARCHAR(32) NOT NULL
label_list_visibility: VARCHAR(32)
message_list_visibility: VARCHAR(32)
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(account_id, gmail_label_id)`

---

### Tabla 6: `calendar_source`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
google_calendar_id: VARCHAR(255) NOT NULL
summary: VARCHAR(255)
primary_flag: BOOLEAN NOT NULL DEFAULT false
selected_flag: BOOLEAN NOT NULL DEFAULT true
timezone: VARCHAR(64)
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(account_id, google_calendar_id)`

---

### Tabla 7: `calendar_event`

```python
id: UUID PK
calendar_source_id: UUID FK -> calendar_source.id (ON DELETE CASCADE)
google_event_id: VARCHAR(255) NOT NULL
status: VARCHAR(32) NOT NULL
summary: VARCHAR(255)
description: TEXT
organizer_email: VARCHAR(255)
attendees_json: JSONB NOT NULL DEFAULT '[]'::jsonb
starts_at: TIMESTAMPTZ
ends_at: TIMESTAMPTZ
all_day: BOOLEAN NOT NULL DEFAULT false
location: VARCHAR(255)
meet_link: VARCHAR(255)
etag: VARCHAR(255)
updated_remote_at: TIMESTAMPTZ
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(calendar_source_id, google_event_id)`

**Índices:**
- PK `id`
- BTREE `(calendar_source_id, starts_at)`
- BTREE `(calendar_source_id, updated_remote_at)`
- GIN `attendees_json`

---

### Tabla 8: `sync_cursor`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
resource_type: VARCHAR(32) NOT NULL  # 'gmail_history' | 'calendar_sync'
resource_key: VARCHAR(255) NOT NULL  # 'inbox' | calendar_id
cursor_value: TEXT
cursor_status: VARCHAR(32) NOT NULL  # 'valid' | 'stale' | 'requires_full_resync'
last_synced_at: TIMESTAMPTZ
last_successful_run_id: UUID FK -> sync_run.id (ON DELETE SET NULL)
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Restricciones:**
- UNIQUE `(account_id, resource_type, resource_key)`

**Índices:**
- PK `id`
- BTREE `(account_id, resource_type, resource_key)`
- BTREE `(resource_type, cursor_status)`

---

### Tabla 9: `sync_run`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
resource_type: VARCHAR(32) NOT NULL
resource_key: VARCHAR(255) NOT NULL
mode: VARCHAR(32) NOT NULL  # 'incremental' | 'full'
status: VARCHAR(32) NOT NULL  # 'running' | 'succeeded' | 'partial' | 'failed'
started_at: TIMESTAMPTZ NOT NULL DEFAULT now()
finished_at: TIMESTAMPTZ
items_seen: INTEGER NOT NULL DEFAULT 0
items_upserted: INTEGER NOT NULL DEFAULT 0
items_deleted: INTEGER NOT NULL DEFAULT 0
error_code: VARCHAR(64)
error_message: TEXT
meta_json: JSONB NOT NULL DEFAULT '{}'::jsonb
```

**Índices:**
- PK `id`
- BTREE `(account_id, resource_type, started_at DESC)`
- BTREE `(status, started_at DESC)`

---

### Tabla 10: `triage_decision`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
thread_id: UUID FK -> gmail_thread.id (ON DELETE CASCADE)
decision_version: VARCHAR(32) NOT NULL
importance_score: NUMERIC(5,4) NOT NULL
confidence_score: NUMERIC(5,4) NOT NULL
requires_response: BOOLEAN NOT NULL
priority_bucket: VARCHAR(32) NOT NULL  # 'critical' | 'high' | 'medium' | 'low' | 'fyi'
reasons_json: JSONB NOT NULL DEFAULT '[]'::jsonb
signals_json: JSONB NOT NULL DEFAULT '{}'::jsonb
calendar_context_json: JSONB NOT NULL DEFAULT '{}'::jsonb
decided_at: TIMESTAMPTZ NOT NULL DEFAULT now()
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- BTREE `(thread_id, decided_at DESC)`
- BTREE `(account_id, priority_bucket, decided_at DESC)`

---

### Tabla 11: `draft_suggestion`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
thread_id: UUID FK -> gmail_thread.id (ON DELETE CASCADE)
triage_decision_id: UUID FK -> triage_decision.id (ON DELETE SET NULL)
status: VARCHAR(32) NOT NULL  # 'proposed' | 'approved' | 'rejected' | 'draft_created'
intent: VARCHAR(32) NOT NULL  # 'acknowledge' | 'ask_clarification' | 'propose_slots' | 'commit' | 'decline'
model_name: VARCHAR(64)
prompt_version: VARCHAR(32) NOT NULL
input_context_hash: VARCHAR(255) NOT NULL
summary_for_user: TEXT NOT NULL
why_this_reply: TEXT NOT NULL
missing_information_json: JSONB NOT NULL DEFAULT '[]'::jsonb
draft_subject: VARCHAR(255)
draft_body_text: TEXT NOT NULL
draft_body_html: TEXT
confidence_score: NUMERIC(5,4) NOT NULL
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- BTREE `(thread_id, created_at DESC)`
- BTREE `(status, created_at DESC)`
- BTREE `(triage_decision_id)`

---

### Tabla 12: `approval_decision`

```python
id: UUID PK
draft_suggestion_id: UUID FK -> draft_suggestion.id (ON DELETE CASCADE)
decision: VARCHAR(32) NOT NULL  # 'approve' | 'reject' | 'edit_then_approve' | 'snooze'
edited_body_text: TEXT
edited_body_html: TEXT
comment: TEXT
decided_by: VARCHAR(255) NOT NULL  # email del usuario
decided_at: TIMESTAMPTZ NOT NULL DEFAULT now()
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- BTREE `(draft_suggestion_id, decided_at DESC)`

---

### Tabla 13: `gmail_draft_binding`

```python
id: UUID PK
draft_suggestion_id: UUID FK -> draft_suggestion.id (ON DELETE CASCADE) UNIQUE
gmail_draft_id: VARCHAR(255) NOT NULL UNIQUE
gmail_message_id: VARCHAR(255)
created_remote_at: TIMESTAMPTZ NOT NULL
last_seen_status: VARCHAR(32) NOT NULL DEFAULT 'created'
created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

### Tabla 14: `audit_event`

```python
id: UUID PK
account_id: UUID FK -> workspace_account.id (ON DELETE CASCADE)
aggregate_type: VARCHAR(64) NOT NULL
aggregate_id: UUID
event_type: VARCHAR(64) NOT NULL
trace_id: VARCHAR(255) NOT NULL
actor_type: VARCHAR(32) NOT NULL  # 'system' | 'human' | 'agent'
actor_id: VARCHAR(255)
payload_json: JSONB NOT NULL DEFAULT '{}'::jsonb
occurred_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Índices:**
- PK `id`
- BTREE `(account_id, occurred_at DESC)`
- BTREE `(aggregate_type, aggregate_id, occurred_at DESC)`
- BTREE `trace_id`

---

## 3. Estrategia de creación

### Fase 1: Crear tablas base (sin FKs cruzadas)
1. `workspace_account`
2. `oauth_credential_ref`
3. `gmail_label_snapshot`
4. `calendar_source`
5. `sync_run` (FK solo a account)

### Fase 2: Crear agregados core
6. `gmail_thread`
7. `gmail_message` (FK a thread)
8. `calendar_event` (FK a calendar_source)

### Fase 3: Sincronización e historial
9. `sync_cursor` (FK a account + nullable a sync_run)
10. `triage_decision` (FK a thread)

### Fase 4: Drafting y auditoría
11. `draft_suggestion` (FK a thread + decision)
12. `approval_decision` (FK a suggestion)
13. `gmail_draft_binding` (FK a suggestion)
14. `audit_event` (FK a account)

---

## 4. Archivo de migración Alembic

**Nombre:** `alembic/versions/20260405_0002_create_correo_agent_schema.py`

**Principios:**
- ✅ Reversible (`upgrade()` ↔ `downgrade()`)
- ✅ Idempotencia en operaciones (DROP IF EXISTS + CREATE IF NOT EXISTS)
- ✅ Índices explícitos en `create_index()`
- ✅ comentarios en SQL para auditoría

---

## 5. Verificación pre-Migration

| Paso | Comando | Expected |
|---|---|---|
| Lint | `ruff check alembic/` | 0 errors |
| Dry-run | `alembic upgrade --sql head` | SQL válido sin errors |
| Upgrade | `alembic upgrade head` | todas 14 tablas creadas |
| Downgrade | `alembic downgrade -1` | todas 14 tablas dropped |
| Upgrade again | `alembic upgrade head` | recreadas sin error |

---

## 6. Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| **FK ciclo** | Strict orden topológico (§3) |
| **Índice mal planeado** | Revisión de queries calientes (doc § 4 en POSTGRES_SCHEMA.md) |
| **Performance downtime** | Crear índices con `CONCURRENTLY` si deploy en prod |
| **Rollback incompleto** | Validar drop de FKs antes de drop de tablas |

---

## 7. Firma de aprobación

### Para proceder a Implement:

- [ ] Lead Tech aprueba orden de creación (§3)
- [ ] DBA aprueba índices y FKs
- [ ] Revisor verifica criterios (§5)

---

## 8. Para la siguiente sesión: Implement

Una vez aprobado, implementaré:
1. ✅ Archivo `20260405_0002_*.py` en Alembic
2. ✅ Validación: upgrade → downgrade → upgrade
3. ✅ Tests de modelo ORM contra schema
