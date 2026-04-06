# ADR-0001 — Arquitectura base del proyecto

- Fecha: 2026-03-18
- Estado: Aceptado

## Contexto
Se requiere un backend mantenible, testeable y preparado para evolución por dominio.
También se requiere trazabilidad operativa y control de calidad desde el inicio.

## Decisión
Adoptar Arquitectura Hexagonal (Clean) con separación en capas:
- `domain`
- `application`
- `infrastructure`
- `entrypoints`

Adoptar además el marco operativo Agents First para ejecución por tareas con evidencia.

## Consecuencias
### Positivas
- Aislamiento del dominio y mejor testabilidad.
- Menor acoplamiento a frameworks/adaptadores.
- Mejor trazabilidad de cambios y verificaciones.

### Costes
- Mayor disciplina inicial de diseño.
- Necesidad de documentar puertos/adaptadores y reglas de dependencia.

## Guardrails
- No lógica de negocio en controladores o repositorios concretos.
- Cualquier cambio de contrato/API/schema requiere gate y aprobación explícita.
- Toda decisión arquitectónica nueva se documenta en ADR.
