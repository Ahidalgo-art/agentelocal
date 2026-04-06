# Plantilla maestra — Inicio de proyecto limpio (Agents First + Arquitectura Hexagonal)

> Propósito: usar este documento como **playbook único de arranque** para nuevos proyectos backend, maximizando calidad, trazabilidad y consistencia desde el día 1.

---

## 1) Objetivo y principios

## Objetivo
Crear un proyecto limpio, mantenible y auditable, con:
- Arquitectura Hexagonal/Clean como base técnica.
- Gobierno operativo Agents First como base de ejecución.
- Gates de calidad, seguridad y operabilidad obligatorios.

## Principios no negociables
1. **Arquitectura primero:** dominio aislado y dependencias hacia adentro.
2. **Evidencia > narrativa:** no hay `DONE` sin evidencia reproducible.
3. **Cambio mínimo correcto:** evitar sobreingeniería y deriva arquitectónica.
4. **Fuente canónica única por tema:** evitar duplicidades documentales.
5. **Stop-the-line:** si falla un gate, no se cierra tarea.

---

## 2) Precedencia de contexto (para evitar confusión)

Definir y respetar siempre esta jerarquía:
1. `/.github/copilot-instructions.md` (arquitectura técnica — máxima prioridad).
2. `/GOVERNANCE.md` (roles, SLA, políticas operativas).
3. `/AGENTS.md` (flujo de agentes IA, gates, DoD).
4. `/QUICKSTART.md` (onboarding breve para devs nuevos).
5. `/PROJECT.md` (estado actual del proyecto).
6. `/docs/adr/` (decisiones técnicas historicales).
7. `/docs/runbooks/` (procedimientos operacionales).
8. Otras fuentes **solo bajo solicitud explícita**.

**Regla de conflicto:** si hay contradicción, prevalece la fuente de máxima prioridad.

---

## 3) Estructura recomendada del repositorio

```text
repo/
  .github/
    copilot-instructions.md
    workflows/
      backend_ci.yml
  AGENTS.md
  PROJECT.md
  backend/
    pyproject.toml
    alembic.ini
    alembic/
    src/
      <app>/
        domain/
        application/
        infrastructure/
        entrypoints/
        main.py
    tests/
    scripts/
  docs/
    adr/
    runbooks/
    checklists/
```

---

## 4) Contratos mínimos de documentación (plantillas obligatorias)

## 4.1 `copilot-instructions.md` (norma arquitectónica)
Debe fijar:
- Arquitectura obligatoria (hexagonal/clean).
- Precedencia de fuentes de contexto.
- Alcance del repo por defecto.
- Restricciones de cambios (no cambiar contratos sin aprobación).

## 4.2 `GOVERNANCE.md` (gobernanza operativa)
Define roles, autorización y políticas. Checklist mínimo:
- RACI: quién aprueba qué decisiones.
- SLA de aprobación por tipo de cambio.
- Policy de agentes IA (presupuesto, scope, cost monitoring).
- Política de versionado de contratos (API, eventos, schema).
- Policy de degradación controlada (cómo fallar elegantemente).
- Anti-duplicidad documental (quién es dueño de qué).

## 4.3 `AGENTS.md` (operación de agentes IA)
Flujo obligatorio y gates de cambios. Incluye:
- Límites de autorización y cambios que requieren pre-aprobación.
- Flujo estándar por tarea (`Understand → Inspect → Plan → Gate → Implement → Verify → Report`).
- Política de veracidad y evidencia.
- Definición de `DONE` con pruebas verificables.

## 4.4 `QUICKSTART.md` (onboarding de 5 minutos)
Debe ser **conciso** y útil para un dev en su primer día:
- Entender arquitectura (hexagonal en 2 min).
- Setup del entorno (comandos de instalación).
- Cómo contribuir (checklist mínimo antes de código).
- Dónde pedir ayuda.

## 4.5 `PROJECT.md` (reinicio rápido)
Estado global ejecutivo en 2–3 pantallas:
- Estado global actual.
- Tareas en curso/bloqueadas.
- Próximo paso recomendado.
- Comandos de sanity check.
- Bitácora corta de pausa/reinicio.

## 4.6 `docs/runbooks/` (procedimientos operacionales)
Guías step-by-step para situaciones reales:
- `operacion_local.md`: environment setup, troubleshooting.
- `degradacion_controlada.md`: cómo fallar elegantemente.
- `observabilidad_checklist.md`: qué es obligatorio en cada endpoint.
- `data_governance.md`: ciclo de vida de datos, auditoría, autorización.
- `politica_secretos_configuracion.md`: manejo seguro de credenciales.

---

## 5) Arquitectura técnica base (Hexagonal)

## Capas
- `domain/`: entidades, value objects, reglas de negocio puras.
- `application/`: casos de uso, puertos (interfaces), orquestación.
- `infrastructure/`: adaptadores concretos (DB, APIs externas, config, seguridad, observabilidad).
- `entrypoints/`: API/CLI/jobs y contratos de entrada/salida.

## Reglas de dependencia
- `entrypoints -> application -> domain`
- `infrastructure` implementa puertos definidos en `application`.
- `domain` no depende de frameworks.

## Política de extensiones permitidas
Se permite añadir capacidades operativas (seguridad, observabilidad, CI, performance) **sin romper** reglas de dependencia ni introducir lógica de negocio en adaptadores.

---

## 6) Know-how operativo que eleva calidad (aprender de este proyecto)

## 6.1 Seguridad por defecto
- Endpoint sensibles con API key/JWT según criticidad.
- Rate limiting mínimo por cliente para operaciones de ingesta/escritura.
- Config segura por entorno: evitar defaults inseguros fuera de `dev`.
- Credenciales NUNCA en código (ver `docs/runbooks/politica_secretos_configuracion.md`).

## 6.2 Observabilidad útil (no cosmética)
- `trace_id` obligatorio en logs y respuestas (ver `docs/runbooks/observabilidad_checklist.md`).
- Métricas de negocio y técnicas separadas.
- Endpoints de salud + dashboard/alertas/export con semántica documentada.
- Checklist por endpoint (auditoría trimestral).

## 6.3 Rendimiento con contratos explícitos
- Usar proyecciones materializadas o caches **solo** con estrategia de refresh/invalidación definida.
- Documentar SLA esperado y coste de consistencia.

## 6.4 Integraciones externas robustas
- Timeouts y manejo de indisponibilidad explícito.
- Modo degradado controlado cuando falle dependencia externa (ver `docs/runbooks/degradacion_controlada.md`).
- Errores funcionales estandarizados (`code`, `message`, `trace_id`).

## 6.5 Ciclo de vida de datos seguro
- Clasificación por sensibilidad.
- Soft-delete por defecto, purga después de retención.
- Auditoría inmutable de acceso y cambios (ver `docs/runbooks/data_governance.md`).

## 6.6 Calidad automatizada en CI
Gates mínimos obligatorios:
1. Lint (`ruff` o equivalente).
2. Tests (cobertura mínima).
3. Migraciones/arranque smoke.
4. Security scan de dependencias (`pip audit`).
5. Anti-tampering check (documentos de gobernanza actualizados vs código).

---

## 7) Anti-duplicidades y anti-incongruencias (punto crítico)

## Problema típico
El proyecto crece y empieza a repetir normas en muchos archivos; con el tiempo se contradicen.

## Política de prevención
- **Una fuente canónica por dominio:**
  - Arquitectura: `copilot-instructions.md`
  - Operación agentes: `AGENTS.md`
  - Estado del proyecto: `PROJECT.md`
  - Decisiones técnicas: `docs/adr/`
- El resto de documentos deben **referenciar**, no duplicar.

## Checklist de coherencia (cada cierre de sprint)
- [ ] ¿Hay reglas repetidas con wording distinto?
- [ ] ¿`PROJECT.md` sigue siendo ejecutivo y breve?
- [ ] ¿Los endpoints de observabilidad tienen semántica consistente entre sí?
- [ ] ¿Hay defaults inseguros en configuración?
- [ ] ¿El runbook coincide con el comportamiento real del código?

---

## 8) Flujo de trabajo estándar por tarea

1. **Intake**
   - Objetivo, alcance, restricciones, supuestos.
2. **Inspect**
   - Revisar patrón existente antes de tocar código.
3. **Plan**
   - Archivos, enfoque, verificación, riesgos.
4. **Gate (previo)**
   - Si requiere aprobación (contratos, schema, seguridad, infra), parar y pedir OK.
5. **Implementación mínima**
   - Dif pequeño, sin cambios colaterales.
6. **Verificación**
   - Ejecutar checks relevantes y guardar evidencia.
7. **Cierre**
   - Resumen, comandos ejecutados, resultados, riesgos residuales.

---

## 9) Definition of Done (DoD) reutilizable

Una tarea solo pasa a `DONE` si existe evidencia de:
- Cambio implementado y trazable.
- Tests/gates ejecutados (o limitación declarada).
- Riesgos residuales documentados.
- Aprobación humana cuando aplique.

Formato recomendado de evidencia por tarea:
- `Command:`
- `Result:`
- `Artifacts:` rutas a reportes/checklists/capturas.

---

## 10) Comandos base (plantilla)

> Ajustar al stack real de AgenteLocal.

```powershell
# Install
cd backend
python -m pip install -e .

# Lint
ruff check src tests

# Tests
$env:PYTHONPATH='src'; pytest -q

# Migrations
alembic upgrade head

# Run API
python -m uvicorn <app>.main:app --host 127.0.0.1 --port 8000

### Documentos de contexto y gobernanza
- [ ] `/.github/copilot-instructions.md` — arquitectura y precedencia.
- [ ] `/GOVERNANCE.md` — roles, SLA, políticas.
- [ ] `/AGENTS.md` — flujo de agentes IA y gates.
- [ ] `/QUICKSTART.md` — onboarding de 5 minutos.
- [ ] `/PROJECT.md` — estado actual ejecutivo.

### Documentación técnica y operacional
- [ ] `/docs/adr/ADR-0001-arquitectura-base.md` — decisión de arquitectura.
- [ ] `/docs/runbooks/operacion_local.md` — setup local y troubleshooting.
- [ ] `/docs/runbooks/politica_secretos_configuracion.md` — manejo de credenciales.
- [ ] `/docs/runbooks/degradacion_controlada.md` — fallos elegantes.
- [ ] `/docs/runbooks/observabilidad_checklist.md` — observable por defecto.
- [ ] `/docs/runbooks/data_governance.md` — ciclo de datos y auditoría.
- [ ] `/docs/checklists/coherencia_anti_duplicidad.md` — validación trimestral.

### Infraestructura y CI
- [ ] `/.github/workflows/backend_ci.yml` — gates (lint + tests + security + smoke).

### Archivos de aplicación (actualizados al contexto real)
- [ ] `/backend/pyproject.toml` — dependencias, metadatos.
- [ ] `/backend/alembic.ini` + `/alembic/env.py` — gestión de migraciones.
- [ ] `/backend/src/<app>/main.py` — entry point de la app.
- [ ] `/backend/src/<app>/domain/` — entidades y reglas de negocio.
- [ ] `/backend/src/<app>/application/` — casos de uso y puertos.
- [ ] `/backend/src/<app>/infrastructure/` — adaptadores.
- [ ] `/backend/src/<app>/entrypoints/api/v1/` — endpoints REST
| Riesgo | Probabilidad | Impacto | Mitigación | Owner |
|---|---|---|---|---|
| Deriva arquitectónica | Media | Alta | Revisiones por capas + ADR breve | arquitecto |
| Defaults inseguros en config | Media | Alta | Fail-fast por entorno + checklist secops | secops |
| Duplicidad documental | Alta | Media | Fuente canónica única y limpieza sprint | documentacion |
| DegraLecciones aprendidas → cambios en plantilla

Al cierre de cada sprint, revisar:

- [ ] ¿Qué patrones se repitieron con dolor?
- [ ] ¿Qué cambios en GOVERNANCE.md ayudarían?
- [ ] ¿Faltan runbooks nuevos?
- [ ] ¿QUICKSTART sigue siendo válido?
- [ ] ¿Hay duplicidad entre documentos?

**Proceso:**
1. Dev propone lección aprendida.
2. Lead Tech valida.
3. Actualizar fuente canónica (GOVERNANCE, runbooks, etc.).
4. Si es decisión arquitectónica: crear ADR nuevo.
5. Comunicar cambio al equipo en standup.

**No dejar pasar:** la calidad mejora solo si formalizamos, no solo si aprendemos
---

## 12) Kit de arranque (copiar al crear nuevo repo)

- [ ] Crear `/.github/copilot-instructions.md` con precedencia y arquitectura.
- [ ] Crear `/AGENTS.md` con reglas operativas y DoD.
- [ ] Crear `/PROJECT.md` ejecutivo de reinicio.
- [ ] Crear `/.github/workflows/backend_ci.yml` con gates (`lint + tests + security + smoke`).
- [ ] Crear `docs/adr/ADR-0001-arquitectura-base.md`.
- [ ] Crear `docs/runbooks/operacion_local.md`.
- [ ] Crear `docs/runbooks/politica_secretos_configuracion.md`.
- [ ] Crear `docs/checklists/coherencia_anti_duplicidad.md`.

---

## 13) Criterio de madurez (rápido)

- **Nivel 1 (Base):** estructura hexagonal + tests + lint.
- **Nivel 2 (Operable):** seguridad de endpoints + trace_id + runbook.
- **Nivel 3 (Confiable):** CI con gates completos + métricas/alertas.
- **Nivel 4 (Escalable):** performance engineering (proyecciones/caché) con contratos de consistencia.

---

## 14) Nota final para siguientes proyectos

Esta plantilla debe versionarse y revisarse al cierre de cada sprint. Toda lección aprendida debe convertirse en una regla concreta o checklist verificable; si no se formaliza, se pierde y la calidad no mejora.
