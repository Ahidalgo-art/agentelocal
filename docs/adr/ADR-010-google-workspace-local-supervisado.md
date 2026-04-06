# ADR-010 — Integración Google Workspace local y supervisada

- **Estado:** Aprobado
- **Fecha:** 2026-04-05

## Contexto

El proyecto necesita acceso a Gmail y Google Calendar para priorizar correos y generar borradores, pero el riesgo operacional y de confianza es alto si se permite actuación autónoma directa sobre la cuenta.

## Decisión

Se adopta un modelo **local-first y supervisado**:
- OAuth local para acceso a Google.
- Lectura de Gmail y Calendar a través de adaptadores específicos.
- Persistencia del estado sincronizado en PostgreSQL.
- El agente consume estado local y no consulta APIs externas libremente durante el razonamiento.
- La única acción remota permitida en esta fase es la **creación de drafts**, siempre tras aprobación humana.

## Consecuencias positivas

- Mayor control y trazabilidad.
- Menor riesgo de acciones no deseadas.
- Mejor depuración del sistema agent-first.
- Capacidad de re-jugar decisiones sobre estado persistido.

## Consecuencias negativas

- Más complejidad inicial de sincronización.
- Latencia mayor frente a “consulta en vivo”.
- Necesidad de gestionar cursores, reauth y full resync.

## Alternativas descartadas

### A. Agente autónomo con acceso directo en cada paso

Descartado por baja auditabilidad y mayor riesgo de comportamiento no deseado.

### B. Integración server-side sin estado local rico

Descartado por peor encaje con el enfoque agent-first y menor capacidad de replay / inspección.
