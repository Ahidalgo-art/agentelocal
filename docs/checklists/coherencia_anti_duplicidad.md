# Checklist — Coherencia y anti-duplicidad documental

## Cuándo usar
- Cierre de cada sprint.
- Antes de release.
- Después de cambios en procesos o arquitectura.

## Fuente canónica por tema
- [ ] Arquitectura solo en `.github/copilot-instructions.md`.
- [ ] Operación/agentes solo en `AGENTS.md`.
- [ ] Estado operativo solo en `PROJECT.md`.
- [ ] Decisiones técnicas en `docs/adr/`.

## Control de duplicidades
- [ ] No hay reglas repetidas con wording distinto en varios docs.
- [ ] No hay comandos contradictorios entre `PROJECT.md` y runbooks.
- [ ] Las reglas de aprobación (gate) están en un único sitio y referenciadas.

## Control de incongruencias
- [ ] El estado de sprint en `PROJECT.md` coincide con tareas reales.
- [ ] Los gates definidos en docs coinciden con CI real.
- [ ] La política de secretos/config coincide con implementación de arranque.
- [ ] Observabilidad: semántica de `health` y métricas documentada y consistente.

## Acción si falla un check
1. Corregir primero la fuente canónica.
2. Actualizar referencias en documentos secundarios.
3. Registrar cambio en bitácora de `PROJECT.md`.
4. Adjuntar evidencia de la corrección.
