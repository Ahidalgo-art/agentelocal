# GOVERNANCE.md

> Propósito: definir roles, autorización y políticas para mantener coherencia arquitectónica y operativa mientras el equipo crece de 5 a 20+ devs.

---

## 1) Roles y autoridad (RACI)

| Decisión | Propone | Valida | Aprueba | Informa |
|---|---|---|---|---|
| **Cambio API / Contrato público** | Dev | Lead Tech | VP Engr | PM |
| **Cambio DB schema / Índices** | Dev | Lead Tech | DBA/Lead | - |
| **Cambio de seguridad / Auth** | Dev | SecOps | VP Engr | - |
| **Introducir nueva dependencia** | Dev | Lead Tech | VP Engr | - |
| **Refactor de capa completa** | Lead Tech | Arch | VP Engr | Dev team |
| **Prioridad: feature vs deuda técnica** | Dev | Lead Tech | PM | Lead Tech |
| **Lección aprendida → cambio en plantilla** | Dev | Lead Tech | Arch | Todo equipo |

---

## 2) SLA de aprobación

Para hacer las cosas predecibles:

| Tipo de cambio | SLA | Estado | Escalada si demora |
|---|---|---|---|
| Menor (<50 líneas, sin contrato) | 4 horas | ∅ | Lead Tech |
| Mayor (>50 líneas, sin schema/API) | 8 horas | ✓ | VP Engr |
| Schema/API/Auth | 24 horas | ✓ | VP Engr |
| Seguridad crítica | 2 horas | ⚠️ URGENTE | CTO/VP Engr (inmediato) |
| Lección aprendida (fin de sprint) | EOD viernes | ✓ | Arch |

---

## 3) Política de Copilot (agente autónomo)

Porque **dinero != ilimitado**.

### 3.1 Presupuesto y límites
- **Presupuesto mensual:** $XXX (ajustar según consumo real)
- **Límite por tarea:** $5–15
- **Tareas excluidas:** las que requieran aprobación previa (schema, API, auth, seguridad)

### 3.2 Qué SÍ puede hacer Copilot sin escalada
- Implementar tests para código existente.
- Refactor interno (mejorar síntaxis, separar funciones).
- Documentación, comentarios, docstrings.
- Bugs menores (typos, lógica obvia).
- Lint/formatting fixes.

### 3.3 Qué NO puede hacer sin aprobación
- Cambios de contrato (API, eventos, DB schema).
- Introducir dependencias nuevas.
- Modificaciones de seguridad/auth.
- Cambios de infraestructura o CI.

### 3.4 Monitoreo
- Una vez por semana: revisar costo de Copilot y usar por tarea.
- Si alguna tarea cuesta >$15: investigar si fue ineficiente y refinar prompt.
- Si mes supera presupuesto: bloquear automático y notify VP Engr.

### 3.5 Rework rate
- Métrica: % de tareas de Copilot que requieren human bounce-back.
- Target: <15% (si sube, reentrenar prompts o cambiar scope).
- Reporte: incluir en Sprint Review.

---

## 4) Política de versionado de contratos

Para evitar breaking changes accidentales:

### 4.1 API (REST)
- **Versiones activas:** 2 en paralelo (ej. `v1`, `v2`).
- **Deprecation:** `v1` → deprecation warning header durante 30 días → EOL.
- **Breaking change:** siempre nueva versión minor (`/v2/endpoint`).
- **Backward compatible change:** same version (`/v1/endpoint` sigue funcionando).

### 4.2 Eventos (async)
- **Versión:** en el payload (`"version": "1.0"`).
- **New field opcional:** same version (old consumers ignoran).
- **New field obligatorio:** nueva versión.
- **Deprecation period:** 30 días + warnings en logs.

### 4.3 DB Schema
- **Forward compatible:** siempre posible (usar migrations reversibles).
- **Rollback window:** 90 días (mantener rollback path).
- **Test:** migration up → smoke test → down → test nuevamente.

---

## 5) Policy de gestión de dependencias

Para evitar dependency hell:

### 5.1 Cuándo actualizar deps
- **Seguridad crítica:** inmediato (<2 horas si impacta API).
- **Seguridad media:** sprint actual.
- **Minor/feature:** máximo cada 2 sprints (prueba primero en dev).
- **Mayor version:** evaluar impacto → aprobación previa.

### 5.2 Sincronización entre proyectos
- Si dos equipos usan misma lib: versión aprobada única (evitar drift).
- Excepción: si un proyecto debe ir delante (pilot), documentar en `meta/DEPENDENCY_LOCK.md`.

### 5.3 Supply chain attack prevention
- Auditar tools: `pip audit` (Python) o equivalente antes de merge.
- Revisar: ¿nueva dependencia tiene <6 meses de edad? ¿<10 stars en GitHub? Investigar.
- CI gate: fallar si hay `CVE-HIGH` o `CVE-CRITICAL` sin waiver explícito.

---

## 6) Políticas de observabilidad (contrato mínimo)

Para que "observable" no sea cosmético:

### 6.1 Qué es obligatorio en TODO endpoint
- **Trace ID:** incluir en log y respuesta (header `X-Trace-ID`).
- **Latency:** registro automático (ms).
- **Status code:** registry by endpoint.
- **Error handling:** `code`, `message`, `trace_id` en respuesta error.

### 6.2 Qué NO es opcional
- No logging sin trace ID.
- No endpoint sin error handling documentado.
- No metrics sin descripción de qué significa.

### 6.3 Dónde van los logs
- **Development:** stdout (prefijo con timestamp + level).
- **Staging/Prod:** centralizado (CloudWatch, ELK, u otro) con indexación por trace_id.

---

## 7) Política de degradación controlada

Para operaciones elegantes cuando algo falla:

### 7.1 Niveles de fallo
- **Nivel 1 (Expected):** exipred cache, retry policy normal (500ms, 3 intentos).
- **Nivel 2 (Partial):** dependencia externa cae → fallback a cached data + warning log.
- **Nivel 3 (Critical):** BD principal cae → HTTP 503 + "service temporarily unavailable" + fallback docs.

### 7.2 Contrato de cliente
- Si un endpoint retorna 503, cliente debe poder reintentar después de 60s.
- Si retorna 200 pero con `"degraded": true`, lógica client puede adaptar.

### 7.3 Documentación per endpoint
Cada endpoint debe tener en docstring:
```python
"""
GET /v1/orders
...
Degradation scenario:
  - Si order_service cae: retorna caché + header `X-Cache-Age: 300s`
  - Si BD principal cae: retorna 503 + retry-after 60s
"""
```

---

## 8) Anti-duplicidad documental

Para evitar que GOVERNANCE, AGENTS y copilot-instructions digan cosas contradictorias:

### 8.1 Fuente canónica
- **Arquitectura técnica:** `.github/copilot-instructions.md` (hexagonal, dependencias).
- **Operación de agentes:** `AGENTS.md` (flujo tasks, gates).
- **Gobernanza + roles + políticas:** `GOVERNANCE.md` (este archivo).
- **Decisiones historicales:** `docs/adr/*.md`.
- **Operación local:** `docs/runbooks/operacion_local.md`.

### 8.2 Si hay conflicto...
1. Revisa cuál es la fuente canónica.
2. Actualiza esa **única** fuente.
3. Referencia la fuente desde otros docs (no duplicar regla).

### 8.3 Auditoría de coherencia (cada 2 sprints)
- [ ] ¿Alguna regla repetida en 2+ documentos con wording distinto?
- [ ] ¿SLA de aprobación coincide entre GOVERNANCE y AGENTS.md?
- [ ] ¿Observabilidad checklist coincide con runbooks?

---

## 9) Escalada de conflictos

Si dos áreas entran en conflicto:

| Conflicto | Responsable | Tiempo |
|---|---|---|
| Dev vs Lead Tech (scope/alcance) | VP Engr | EOD hoy |
| Dev vs SecOps (seguridad) | CTO/VP Engr | <2h (blocking) |
| Architecture vs Producto (feature vs deuda) | VP Product + VP Engr | <24h |
| Sprints duros sin descanso → burnout | VP Engr | EOW (end of week) |

---

## 10) Actualización de esta política

Esta política se revisa cada 2 sprints en "Governance+Architecture Sync":
- [ ] ¿SLA realista o sobreestimada?
- [ ] ¿Roles coinciden con equipo actual?
- [ ] ¿Copilot cost en línea con presupuesto?
- [ ] ¿Lecciones aprendidas → cambios que hacer aquí?

Si hay cambio significativo: crear ADR (`docs/adr/ADR-XXXX-governance-change.md`).

---

## 11) Branching strategy

| Rama | Propósito | Push directo permitido |
|---|---|---|
| `main` | Producción, siempre deployable | ❌ Solo via PR aprobado |
| `develop` | Integración continua | ❌ Solo via PR del equipo |
| `feature/XXXX-descripcion` | Features y bugfixes | ✅ Dev individual |
| `hotfix/XXXX-descripcion` | Fix urgente a producción | Solo Lead Tech |

**Requisitos de PR antes de merge a `main` o `develop`:**
- [ ] CI pasando (lint, tests, security, architecture)
- [ ] Revisión de al menos 1 miembro del equipo
- [ ] Tests de la feature incluidos en el PR
- [ ] Sin `TODO` sin fecha o ticket asignado

**Quién revisa qué:**
- Feature → cualquier miembro del equipo
- Cambio de contrato API → Lead Tech obligatorio
- Cambio de schema DB → Lead Tech + DBA obligatorio
- Hotfix a main → Lead Tech y aprobación VP Engr

---

## 12) Proceso técnico de aprobación

**Cómo solicitar aprobación para un gate:**
1. Abrir PR con prefijo `[APPROVAL NEEDED]` en el título.
2. Añadir label `needs-approval` en GitHub.
3. Mencionar al aprobador con `@nombre` en el cuerpo del PR.
4. Si no hay respuesta en el SLA → escalar según sección 9 (Escalada).
5. Si el aprobador está ausente → actúa el backup definido abajo.

**Backup de aprobadores (para ausencias):**

| Rol | Titular | Backup |
|---|---|---|
| Lead Tech | [NAME - Lead Tech] | [BACKUP NAME] |
| VP Engr | [NAME - VP Engr] | [BACKUP NAME] |
| DBA/Lead | [NAME - DBA] | [BACKUP NAME] |

> Rellenar `[NAME]` y `[BACKUP NAME]` antes del primer sprint real.

---

## Apéndice: Ejemplo de PRContext (primer PR)

```markdown
## PR: Add GET /v1/orders endpoint

### Governance Checklist
- [ ] Cambio de contrato API: SÍ → esperar aprobación Lead Tech (24h SLA)
- [ ] Cambio de schema: NO
- [ ] Seguridad: NO
- [ ] Nueva dependencia: NO
- [ ] Error handling doc: SÍ (incluido en PR)
- [ ] Observabilidad (trace_id, latency, error codes): SÍ

### Aprobaciones requeridas
- [ ] Lead Tech (API review)
- [ ] PM (feature clarification)

### Status
⏳ Waiting for Lead Tech approval (opened 2026-03-18T10:00Z, SLA expires 2026-03-19T10:00Z)
```
