# SPEC — Agente local Gmail + Google Calendar

## 1. Propósito

Construir un agente local, supervisado y orientado a herramientas, que consuma Gmail y Google Calendar, persista su estado en PostgreSQL y ayude al usuario a:

1. detectar correos importantes;
2. justificar por qué los considera importantes;
3. generar propuestas de respuesta;
4. crear borradores en Gmail solo con aprobación humana.

## 2. Objetivos del sistema

### Objetivos funcionales

- Sincronizar mensajes, hilos, labels y cambios incrementales de Gmail.
- Sincronizar calendarios y eventos relevantes de Google Calendar.
- Priorizar hilos que requieren atención o respuesta.
- Enriquecer la decisión con contexto de agenda.
- Producir borradores de respuesta trazables.
- Mantener auditoría y estado operacional en PostgreSQL.

### Objetivos no funcionales

- Arquitectura local-first.
- Persistencia transaccional y auditable.
- Idempotencia en sync y creación de propuestas.
- Human-in-the-loop para toda acción que genere artefactos en Gmail.
- Trazabilidad completa de decisión, scoring y prompts efectivos.
- Degradación controlada cuando fallen OAuth, sync tokens o cuotas.

## 3. Alcance

### Incluido en esta fase

- OAuth local con Google.
- Lectura de Gmail.
- Lectura de Calendar.
- Scoring de importancia.
- Propuesta de borrador en aplicación local.
- Creación de draft en Gmail tras aprobación.
- Persistencia en PostgreSQL local.
- Observabilidad de operaciones y auditoría.

### Fuera de alcance en esta fase

- Envío automático de correos.
- Respuesta autónoma sin revisión humana.
- Etiquetado automático irreversible.
- Push realtime en producción.
- Multiusuario/multitenant.
- Entrenamiento online del modelo.

## 4. Suposiciones de diseño

- El usuario opera una única cuenta principal de Google Workspace o Gmail personal por instancia del sistema.
- La base de datos PostgreSQL es local y de confianza operativa.
- El backend ya existe; este proyecto añade documentación y contratos específicos.
- El orquestador agent-first invoca herramientas explícitas y no accede directamente a APIs externas sin pasar por puertos/adaptadores.

## 5. Principios específicos del proyecto

1. **El agente decide sobre estado local, no sobre APIs remotas en caliente.**
2. **Toda acción en Gmail debe ser reversible o no destructiva.**
3. **La explicación de por qué un correo es importante es obligatoria.**
4. **La creación de borrador requiere aprobación humana explícita.**
5. **Las decisiones del agente deben quedar auditadas con input, output y evidencia mínima.**
6. **El contexto de Calendar solo se usa para enriquecer la propuesta, no para actuar sobre la agenda.**

## 6. Capacidades del sistema

### C1. Ingesta de Gmail

El sistema obtiene:
- mensajes;
- hilos;
- labels;
- headers relevantes;
- snippets;
- cuerpo normalizado para candidatos shortlistados;
- historyId para sync incremental.

### C2. Ingesta de Calendar

El sistema obtiene:
- calendarios visibles;
- eventos en ventanas temporales configurables;
- asistentes;
- disponibilidad contextual;
- syncToken para deltas.

### C3. Triage

El sistema puntúa la importancia de un hilo mediante:
- reglas deterministas;
- señales semánticas;
- contexto de agenda;
- historial del propio sistema.

### C4. Drafting

El sistema propone una respuesta con:
- resumen del contexto;
- intención detectada;
- borrador textual;
- nivel de confianza;
- datos faltantes o ambigüedades;
- explicación del porqué de la propuesta.

### C5. Aprobación y draft

El usuario puede:
- aprobar sin cambios;
- editar antes de crear draft;
- rechazar la propuesta;
- posponer;
- marcar el hilo como no relevante para aprendizaje posterior.

## 7. Actores

- **Usuario operador**: revisa shortlist, aprueba o corrige borradores.
- **Agente orquestador**: coordina herramientas y flujo.
- **Conector Gmail**: adaptador de infraestructura.
- **Conector Calendar**: adaptador de infraestructura.
- **Repositorio PostgreSQL**: store operacional y de auditoría.
- **Modelo LLM**: scoring explicable y redacción asistida.

## 8. Casos de uso principales

### UC-01 — Sincronizar bandeja y agenda

**Trigger:** job manual o programado.

**Resultado esperado:** PostgreSQL queda actualizado con mensajes, hilos, labels, eventos y cursores de sincronización.

### UC-02 — Obtener shortlist de correos importantes

**Trigger:** solicitud del usuario o job de triage.

**Resultado esperado:** lista priorizada de hilos con score, razones y acción sugerida.

### UC-03 — Proponer borrador para hilo

**Trigger:** usuario selecciona un hilo o el sistema genera propuestas para shortlist.

**Resultado esperado:** propuesta estructurada y borrador textual persistidos.

### UC-04 — Crear draft en Gmail

**Trigger:** aprobación humana.

**Resultado esperado:** draft creado en Gmail y vinculado a la propuesta local.

### UC-05 — Recuperación ante desincronización

**Trigger:** `historyId` inválido, `syncToken` expirado, cambio de scopes o token revocado.

**Resultado esperado:** full resync controlado, auditoría del incidente y reanudación consistente.

## 9. Reglas de negocio

- RB-01: un hilo no puede pasar a estado `draft_created` sin transición previa por `approved`.
- RB-02: un borrador no puede generarse si el hilo está clasificado como FYI con confianza alta.
- RB-03: si el hilo implica coordinación temporal y no existe contexto suficiente de agenda, la propuesta debe indicar falta de información.
- RB-04: el sistema no enviará mensajes, solo creará drafts.
- RB-05: toda propuesta debe incluir `why_this_is_important`.
- RB-06: si el scoring es inferior al umbral mínimo configurable, no se invoca drafting automático.
- RB-07: cada ejecución debe ser idempotente para el mismo cursor de sync.

## 10. Modelo conceptual de dominio

### Entidades

- **MailboxAccount**
- **GmailThread**
- **GmailMessage**
- **CalendarEvent**
- **TriageDecision**
- **DraftSuggestion**
- **ApprovalDecision**
- **SyncCursor**
- **AuditEvent**

### Value Objects

- EmailAddress
- ImportanceScore
- ConfidenceScore
- SyncWindow
- GmailHistoryCursor
- CalendarSyncCursor
- DraftIntent

## 11. Estados clave

### Estado del hilo respecto al agente

- `discovered`
- `synced`
- `triaged`
- `shortlisted`
- `enriched`
- `draft_proposed`
- `approved`
- `draft_created`
- `rejected`
- `snoozed`

### Estado operacional de sync

- `idle`
- `running`
- `succeeded`
- `partial`
- `failed`
- `needs_full_resync`

## 12. Flujo de alto nivel

1. Descubrir cambios en Gmail y Calendar.
2. Persistir cambios brutos normalizados.
3. Seleccionar candidatos al triage.
4. Calcular score de importancia y razones.
5. Enriquecer con thread completo y contexto de agenda.
6. Generar propuesta estructurada.
7. Esperar aprobación humana.
8. Crear draft en Gmail.
9. Registrar auditoría y feedback.

## 13. Integraciones externas

### Gmail

Permisos deseados en esta fase:
- lectura de correo;
- creación de borradores.

### Google Calendar

Permisos deseados en esta fase:
- lectura de calendarios y eventos.

## 14. Política de aprobación

### Requiere aprobación humana obligatoria

- crear draft en Gmail;
- regenerar borrador con diferente intención;
- usar instrucciones de estilo persistidas nuevas;
- reintentar draft cuando cambie el contexto de agenda.

### No requiere aprobación humana

- sync incremental;
- triage;
- enriquecimiento de contexto;
- cálculo de shortlist.

## 15. Observabilidad mínima requerida

Cada operación relevante debe registrar:
- `trace_id`
- `account_id`
- `thread_id` o `event_id` cuando aplique
- tipo de operación
- duración
- resultado
- contador de elementos afectados
- causa de fallo si existe

Métricas mínimas:
- tiempo de sync Gmail
- tiempo de sync Calendar
- número de hilos triados
- ratio shortlist/triaged
- número de drafts propuestos
- número de drafts aprobados
- número de drafts creados
- número de full resyncs

## 16. Seguridad y privacidad

- Tokens OAuth cifrados en reposo o referenciados vía secret store local.
- Cuerpo completo del mensaje solo cuando sea necesario para triage avanzado o drafting.
- Redacción/mascarado de secretos en logs.
- Auditoría inmutable de aprobación y creación de drafts.
- Posibilidad de purga selectiva de contenido persistido.

## 17. Criterios de aceptación de la primera entrega

### Funcionales

- El sistema sincroniza correo y agenda contra PostgreSQL.
- El sistema devuelve shortlist priorizado con explicación.
- El sistema genera borrador para un hilo seleccionado.
- El usuario puede aprobar y crear draft en Gmail.

### Técnicos

- Sync incremental implementado para Gmail y Calendar.
- Soporte de full resync controlado.
- Tablas e índices operativos definidos.
- Auditoría y trazabilidad disponibles.
- Tests de integración para adaptadores y repositorios.

## 18. Riesgos específicos

- Expiración de cursores o tokens de sync.
- Scope drift entre entorno local y configuración de Google.
- Borradores incorrectos por contexto insuficiente.
- Coste de almacenamiento si se persiste demasiado payload bruto.
- Exceso de acoplamiento entre heurísticas y prompts.

## 19. Decisiones diferidas

- Uso o no de embeddings para memoria de estilo y recuperación de contexto.
- Push vs polling como mecanismo principal.
- Multicuenta.
- Etiquetado automático opcional en Gmail.
- Incorporación de contactos o CRM como fuente adicional.
