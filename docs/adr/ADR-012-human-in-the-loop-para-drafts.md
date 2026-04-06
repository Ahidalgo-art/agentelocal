# ADR-012 — Human-in-the-loop obligatorio para drafts

- **Estado:** Aprobado
- **Fecha:** 2026-04-05

## Contexto

El objetivo del sistema es acelerar la gestión del correo sin comprometer control, tono, precisión ni seguridad operativa.

## Decisión

Toda creación de draft remoto en Gmail requerirá aprobación humana explícita previa.

No se habilita en esta fase:
- envío automático;
- respuesta automática;
- aprobación implícita por score alto.

## Razones

- Los correos afectan relación profesional, compromiso temporal y reputación.
- La agenda puede introducir ambigüedades que el modelo no resuelva correctamente.
- La revisión humana permite recopilar feedback útil para calibrar el sistema.

## Consecuencias

### Positivas

- Riesgo operacional muy inferior.
- Mayor confianza inicial en el sistema.
- Ciclo de aprendizaje explícito sobre correcciones humanas.

### Negativas

- Menor automatización total.
- Un paso adicional antes de materializar el draft.

## Revisión futura

Solo se reconsiderará relajación de esta política si existen métricas sostenidas de calidad y controles adicionales por tipo de correo.
