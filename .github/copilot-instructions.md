# Instrucciones de Copilot — Proyecto nuevo (Arquitectura Hexagonal)

## Política de idioma

| Contexto | Idioma |
|---|---|
| Código (variables, funciones, clases, módulos) | Inglés |
| Comentarios en código | Inglés |
| Commits y PR descriptions | Inglés |
| Documentos de gobernanza (GOVERNANCE, AGENTS, PROJECT) | Español |
| Runbooks y ADRs | Español |
| Mensajes de error retornados por la API | Inglés |
| Logs de aplicación | Inglés |

---

## Prioridad de contexto (obligatoria)
1. Arquitectura: este archivo + guía/skill de Arquitectura Hexagonal.
2. Operación de agentes: `AGENTS.md`.
3. Requisitos externos o análisis históricos: solo cuando el humano lo pida explícitamente.

Si hay conflicto entre fuentes, prevalece la arquitectura definida aquí.

## Regla arquitectónica
- Usar Arquitectura Hexagonal / Clean.
- Separación mínima de capas:
  - `domain`: reglas de negocio puras.
  - `application`: casos de uso y puertos.
  - `infrastructure`: adaptadores concretos.
  - `entrypoints`: API/CLI/jobs.
- Dependencias hacia adentro (`entrypoints -> application -> domain`).
- Prohibido mover lógica de negocio a adaptadores o controladores.

## Alcance y precisión
- Realizar cambios mínimos, trazables y coherentes con patrones existentes.
- Evitar refactors no solicitados.
- No introducir dependencias o cambios de contrato sin aprobación explícita.

## Criterio de calidad
- No marcar trabajo como finalizado sin evidencia verificable.
- Para cada cambio no trivial: incluir verificación (tests/lint/build o limitación explícita).

## Restricción anti-confusión
- Mantener una sola fuente canónica por tema:
  - Arquitectura: este archivo.
  - Operación y autorización de cambios: `AGENTS.md`.
  - Estado y reinicio del proyecto: `PROJECT.md`.
  - Decisiones técnicas: `docs/adr/`.
- El resto de documentos deben referenciar, no duplicar reglas.
