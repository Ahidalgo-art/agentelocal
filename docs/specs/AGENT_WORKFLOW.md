# SPEC — Workflow agent-first

## 1. Objetivo

Definir el workflow del agente de correo y calendario como una cadena de capacidades pequeñas, trazables y supervisadas.

## 2. Filosofía operativa

El agente:
- no navega libremente por Gmail ni Calendar;
- consume puertos definidos;
- trabaja sobre estado persistido;
- delega en el usuario toda acción con impacto externo visible.

## 3. State machine

```text
sync_pending
  -> synced
  -> triaged
  -> shortlisted
  -> enriched
  -> draft_proposed
  -> approved
  -> draft_created

Ramas alternativas:
shortlisted -> rejected
shortlisted -> snoozed
draft_proposed -> rejected
draft_proposed -> superseded
```

## 4. Etapas

### Etapa A — Sync

Entradas:
- cuenta conectada
- cursor Gmail
- cursores Calendar

Salidas:
- mensajes/hilos/eventos actualizados
- `sync_run`
- `sync_cursor`

### Etapa B — Candidate selection

Entradas:
- hilos sincronizados recientes
- configuración de ventana temporal

Reglas mínimas:
- preferir inbox/unread/recentes;
- excluir ruido conocido configurable;
- excluir hilos ya resueltos o snoozed vigentes.

### Etapa C — Triage

Entradas:
- metadata del hilo
- señales de remitente
- señales de labels
- señales temporales

Salidas:
- `triage_decision`
- bucket de prioridad
- razones explicables

### Etapa D — Enrichment

Entradas:
- hilo shortlistado
- últimos mensajes del thread
- ventana de agenda relevante

Salidas:
- contexto expandido
- necesidad real de respuesta
- tipo de acción sugerida

### Etapa E — Draft generation

Entradas:
- triage final
- contexto expandido
- preferencias de tono

Salidas:
- `draft_suggestion`
- texto del borrador
- carencias de información
- score de confianza

### Etapa F — Human approval

Entradas:
- `draft_suggestion`

Decisiones posibles:
- aprobar
- editar y aprobar
- rechazar
- posponer

Salidas:
- `approval_decision`
- cambio de estado

### Etapa G — Draft create

Precondición:
- aprobación válida

Salidas:
- draft remoto en Gmail
- `gmail_draft_binding`
- `audit_event`

## 5. Políticas de stop-the-line

El agente debe parar y escalar a intervención humana si:
- el cursor incremental es inválido;
- cambia el set de scopes efectivo;
- el hilo incluye ambigüedad crítica;
- el contexto de agenda es insuficiente para una propuesta temporal;
- el LLM devuelve una intención incoherente con las reglas del sistema;
- el adaptador Gmail devuelve error en creación de draft.

## 6. Inputs mínimos para triage

- asunto
- remitente
- snippet
- labels
- unread
- recencia
- si el último mensaje es inbound
- participantes
- señales de historial local

## 7. Inputs mínimos para drafting

- últimos mensajes relevantes del hilo
- última decisión de triage
- contexto de agenda en ventana útil
- preferencias de tono activas
- tipo de respuesta deseado

## 8. Outputs estructurados recomendados

### Triage output

```json
{
  "requires_response": true,
  "importance_score": 0.91,
  "priority_bucket": "high",
  "reasons": [
    "cliente relevante",
    "pregunta explícita",
    "impacto temporal esta semana"
  ],
  "next_action": "generate_draft"
}
```

### Draft output

```json
{
  "intent": "propose_slots",
  "summary_for_user": "El remitente pide una reunión esta semana y el calendario muestra dos huecos posibles.",
  "why_this_reply": "Conviene responder con slots concretos y tono ejecutivo breve.",
  "missing_information": [],
  "draft_body_text": "...",
  "confidence_score": 0.84
}
```

## 9. Feedback loop

El feedback humano debe alimentar:
- ranking de remitentes importantes;
- umbrales de shortlist;
- intención preferida de respuesta;
- estilo y longitud de borradores;
- falsas alarmas del triage.

## 10. Métricas de calidad

- precision@k del shortlist;
- ratio de borradores aprobados sin edición;
- ratio de borradores aprobados con edición menor;
- tasa de falsos positivos FYI vs reply-needed;
- tiempo medio desde shortlist hasta aprobación.
