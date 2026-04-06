# Runbook — Sincronización y recuperación

## 1. Objetivo

Operar y recuperar el pipeline de sincronización Gmail + Calendar cuando existan fallos de cursores, deltas inconsistentes o errores parciales.

## 2. Modos soportados

- incremental
- full resync

## 3. Señales de salud

- `sync_run.status = succeeded` de forma sostenida;
- `sync_cursor.cursor_status = valid`;
- backlog de hilos sin triage dentro de umbral aceptable;
- ratio de errores bajo.

## 4. Gmail incremental

Entrada:
- cursor de tipo `gmail_history`

Proceso:
1. abrir `sync_run` incremental;
2. leer cambios desde cursor actual;
3. aplicar upserts en hilos/mensajes;
4. actualizar cursor al último punto consistente;
5. cerrar `sync_run`.

## 5. Calendar incremental

Entrada:
- cursor de tipo `calendar_sync` por calendario

Proceso:
1. abrir `sync_run` incremental;
2. pedir delta por `syncToken`;
3. aplicar altas/bajas/cambios;
4. persistir nuevo token;
5. cerrar `sync_run`.

## 6. Recuperación por cursor Gmail inválido

Síntomas:
- error remoto de cursor/history inválido;
- delta incompleto;
- inconsistencia entre mensajes recientes y estado local.

Acciones:
1. marcar `sync_cursor.cursor_status = requires_full_resync`;
2. registrar `audit_event`;
3. lanzar `sync_run` full;
4. reconstruir estado del recurso afectado;
5. reabrir incremental solo cuando el full termine correctamente.

## 7. Recuperación por sync token Calendar caducado

Acciones:
1. marcar cursor del calendario como stale;
2. purgar slice sincronizable afectado si la estrategia lo requiere;
3. ejecutar full resync para ese calendario;
4. verificar nuevos eventos y token final.

## 8. Reglas de seguridad operacional

- nunca avanzar un cursor si la transacción lógica de persistencia no cerró bien;
- no mezclar full e incremental sobre el mismo recurso simultáneamente;
- usar locks lógicos por `account_id + resource_type + resource_key`.

## 9. Checklist de cierre

- cursor final válido;
- sync_run cerrado;
- shortlist actualizado;
- eventos de auditoría emitidos;
- sin drafts en estados imposibles.
