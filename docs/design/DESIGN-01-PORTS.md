# DESIGN-01: Contratos de puertos — Agente Correo-Calendar

**Estado:** 🔵 En propuesta (GATE: requiere aprobación Lead Tech)  
**Fecha:** 2026-04-05  
**Impacto:** 🔴 Alto — Define abstracciones nucleares de `application/ports/`

---

## 1. Objetivo

Definir interfaces abstractas (protocolos Python) para desacoplar:
- Sincronización Gmail (lectura de hilos, mensajes, history)
- Sincronización Calendar (eventos)
- Persistencia (repositorios de entidades)
- Triage (scoring de importancia)
- Drafting (generación de borradores)

**Principio:** El dominio NO conoce implementación concreta (Google API client, SQLAlchemy, LLM).

---

## 2. Puertos propuestos

### 2.1 SyncCursor Port

```python
# application/ports/sync_cursor.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class CursorState:
    """Estado de cursor — valor + status."""
    value: Optional[str]
    status: str  # valid | stale | requires_full_resync
    last_synced_at: Optional[datetime]
    runs_count: int

class SyncCursorPort(ABC):
    """Gestión de cursores incremental por recurso."""
    
    @abstractmethod
    async def get_cursor(
        self, 
        account_id: str, 
        resource_type: str,      # gmail_history | calendar_sync
        resource_key: str,        # inbox | calendar_id
    ) -> CursorState:
        """Obtiene cursor actual."""
        pass

    @abstractmethod
    async def update_cursor(
        self,
        account_id: str,
        resource_type: str,
        resource_key: str,
        cursor_value: Optional[str],
        new_status: str,
        sync_run_id: str,
    ) -> None:
        """Actualiza cursor tras sync exitoso."""
        pass

    @abstractmethod
    async def mark_stale(
        self,
        account_id: str,
        resource_type: str,
        resource_key: str,
    ) -> None:
        """Marca cursor como forzosamente obsoleto (requiere full resync)."""
        pass
```

**Criterios de validación:**
- ✅ Sin dependencia a Google API o SQLAlchemy
- ✅ Async native (compatible con FastAPI + uvicorn)
- ✅ Estados explícitos (valid | stale | requires_full_resync)

---

### 2.2 GmailSyncPort

```python
# application/ports/gmail_sync.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class EmailThread:
    """Agregado de conversación."""
    gmail_thread_id: str
    subject_normalized: Optional[str]
    last_message_at: Optional[datetime]
    message_count: int
    has_unread: bool
    is_important_label: bool
    participants_cache: dict  # {email: name}

@dataclass(frozen=True)
class EmailMessage:
    """Mensaje individual."""
    gmail_message_id: str
    gmail_internal_date_at: Optional[datetime]
    sender_email: Optional[str]
    snippet: Optional[str]
    is_inbound: bool
    labels: List[str]

class GmailSyncPort(ABC):
    """Lectura de Gmail en modo incremental."""
    
    @abstractmethod
    async def list_threads(
        self,
        account_id: str,
        history_id: Optional[str] = None,  # None = full resync
        limit: int = 100,
    ) -> tuple[list[EmailThread], Optional[str]]:
        """
        Lista hilos modificados desde history_id.
        Retorna: (threads, next_history_id)
        """
        pass

    @abstractmethod
    async def get_thread_messages(
        self,
        account_id: str,
        thread_id: str,
    ) -> list[EmailMessage]:
        """Obtiene todos los mensajes de un hilo."""
        pass

    @abstractmethod
    async def get_message_full(
        self,
        account_id: str,
        message_id: str,
    ) -> dict:
        """
        Obtiene payload completo: body_text, body_html, headers.
        Retorna dict con claves: body_text, body_html, headers_json
        """
        pass

    @abstractmethod
    async def mark_as_read(
        self,
        account_id: str,
        message_ids: list[str],
    ) -> None:
        """Marca mensajes como leídos."""
        pass
```

**Criterios de validación:**
- ✅ Métodos separados por responsabilidad (list ≠ get_full)
- ✅ Historia incremental explícita (history_id)
- ✅ Retorna dataclasses, no objetos externos

---

### 2.3 CalendarSyncPort

```python
# application/ports/calendar_sync.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class CalendarEvent:
    """Evento de agenda."""
    google_event_id: str
    status: str  # confirmed | tentative | cancelled
    summary: Optional[str]
    organizer_email: Optional[str]
    attendees: List[dict]  # {email: str, response_status: str}
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    all_day: bool
    location: Optional[str]
    meet_link: Optional[str]

class CalendarSyncPort(ABC):
    """Lectura de calendario para contexto."""
    
    @abstractmethod
    async def list_calendars(
        self,
        account_id: str,
    ) -> List[dict]:
        """Retorna lista de calendarios: [id, summary, primary_flag]."""
        pass

    @abstractmethod
    async def list_events(
        self,
        account_id: str,
        calendar_id: str,
        sync_token: Optional[str] = None,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> tuple[list[CalendarEvent], Optional[str]]:
        """
        Lista eventos.
        Si sync_token: incremental.
        Si time_min/time_max: ventana fija.
        Retorna: (events, next_sync_token)
        """
        pass
```

---

### 2.4 ThreadRepositoryPort

```python
# application/ports/thread_repository.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class ThreadEntity:
    """Entidad persisted de hilo."""
    id: str  # UUID local
    account_id: str
    gmail_thread_id: str
    subject_normalized: Optional[str]
    message_count: int
    has_unread: bool
    agent_state: str  # discovered | triaged | draft_proposed | approved | created
    triage_decision_id: Optional[str]
    draft_suggestion_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class ThreadRepositoryPort(ABC):
    """CRUD sobre hilos."""
    
    @abstractmethod
    async def upsert(
        self,
        account_id: str,
        gmail_thread_id: str,
        subject: Optional[str],
        **fields,
    ) -> ThreadEntity:
        """Insert o update (idempotente)."""
        pass

    @abstractmethod
    async def get_by_id(self, thread_id: str) -> Optional[ThreadEntity]:
        """Obtiene por UUID local."""
        pass

    @abstractmethod
    async def get_by_gmail_id(
        self,
        account_id: str,
        gmail_thread_id: str,
    ) -> Optional[ThreadEntity]:
        """Obtiene por gmail_thread_id."""
        pass

    @abstractmethod
    async def list_by_state(
        self,
        account_id: str,
        state: str,
        limit: int = 100,
    ) -> list[ThreadEntity]:
        """Lista por agent_state para procesamiento."""
        pass

    @abstractmethod
    async def update_state(
        self,
        thread_id: str,
        new_state: str,
    ) -> ThreadEntity:
        """Cambia estado."""
        pass
```

---

### 2.5 TriageServicePort

```python
# application/ports/triage_service.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class TriageResult:
    """Resultado de triage."""
    thread_id: str
    importance_score: float  # 0.0 — 1.0
    confidence_score: float
    priority_bucket: str  # critical | high | medium | low | fyi
    requires_response: bool
    reasons: List[str]
    signals: dict

class TriageServicePort(ABC):
    """Decisión de importancia."""
    
    @abstractmethod
    async def score_thread(
        self,
        thread_id: str,
        participants: List[str],
        subject: str,
        latest_snippet: str,
        calendar_context: dict,  # {days_ahead: events}
    ) -> TriageResult:
        """Calcula importancia y prioridad."""
        pass
```

---

### 2.6 DraftingServicePort

```python
# application/ports/drafting_service.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class DraftProposal:
    """Propuesta de borrador."""
    thread_id: str
    intent: str  # acknowledge | ask_clarification | propose_slots | commit | decline
    summary_for_user: str
    why_this_reply: str
    draft_subject: str
    draft_body_text: str
    confidence_score: float

class DraftingServicePort(ABC):
    """Generación de propuestas de respuesta."""
    
    @abstractmethod
    async def propose_draft(
        self,
        thread_id: str,
        subject: str,
        latest_sender: str,
        message_snippet: str,
        calendar_context: dict,
    ) -> DraftProposal:
        """Propone texto para borrador."""
        pass
```

---

## 3. Ubicación en árbol de capas

```
backend/src/agente_local/
├── domain/                       ← Entidades puras (sin frameworks)
│   ├── email_thread.py           ← ValueObjects
│   ├── sync_run.py
├── application/
│   ├── ports/                ← ⭐ NUEVA — Interfaces abstractas
│   │   ├── __init__.py
│   │   ├── sync_cursor.py
│   │   ├── gmail_sync.py
│   │   ├── calendar_sync.py
│   │   ├── thread_repository.py
│   │   ├── triage_service.py
│   │   └── drafting_service.py
│   └── services/
│       ├── sync_orchestrator.py   ← Caso de uso: orquesta puertos
│       └── draft_approval.py      ← Caso de uso: aprobación humana
├── infrastructure/
│   └── persistence/
│       ├── sqlalchemy_repos.py    ← Implementa ThreadRepositoryPort
│       ├── gmail_adapter.py       ← Implementa GmailSyncPort
│       ├── calendar_adapter.py    ← Implementa CalendarSyncPort
│       ├── triage_impl.py         ← Implementa TriageServicePort
│       └── models.py              ← SQLAlchemy ORM
└── entrypoints/
    └── api/v1/endpoints/
        ├── sync.py               ← POST /v1/sync
        ├── triage.py             ← GET /v1/threads?state=triaged
        └── drafts.py             ← POST /v1/drafts/{id}/approve
```

---

## 4. Criterios de validación

| Criterio | Esperado | Razón |
|---|---|---|
| **Lenguaje** | 100% inglés | Contratos públicos de arquitectura |
| **Tipado** | `ABC`, `abstractmethod` | Explícito para Pylance + verificación estática |
| **Async native** | `async def` / `await` | Compatible con FastAPI + uvicorn |
| **Sin imports framework** | No FastAPI, SQLAlchemy, Google | Aislado de infraestructura |
| **Dataclasses congeladas** | `@dataclass(frozen=True)` | Immutabilidad por defecto |
| **Optional explícito** | `Optional[T]` | Evita `None` implícito |

---

## 5. Riesgos y mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| **Cambio en API de Google** | 🔴 Alta | 🔴 Alto | Envolver Google client en adapter; versionar puerto |
| **Contrato de puerto incompleto** | 🟡 Media | 🟡 Media | Tests de integración lo revelan rápido; iterable |
| **Performance del cursor** | 🟢 Baja | 🟡 Media | Índice en `(account_id, resource_type, resource_key)` |

---

## 6. Firma de aprobación

### Para procedera a Implement:

- [ ] Lead Tech aprueba contratos
- [ ] Revisor verifica criterios de validación (§4)
- [ ] Sin cambios a tabla `domain/` ni entrypoints

---

## 7. Para la siguiente sesión: Implement

Una vez aprobado, implementaré:
1. ✅ Archivos de ports en `application/ports/`
2. ✅ Tests de contratos (mock implementations)
3. ✅ Validación de Pylance sin errores
