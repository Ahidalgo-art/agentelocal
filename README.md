# 🏗️ Plantilla Maestra: Inicio de Proyecto Backend (Agents First + Hexagonal)

> Especificaciones y documentación de referencia para crear nuevos proyectos backend con **Arquitectura Hexagonal + Gobernanza de Agentes IA**.

---

## 🚀 ¿Por dónde empezar?

### Para trabajar AgenteLocal desde cero:

**👉 [INSTRUCCIONES_INICIO_PROYECTO.md](INSTRUCCIONES_INICIO_PROYECTO.md)** (30 minutos de lectura)

Esta guía cubre:
- Decisiones previas (naming, stack, ownership).
- Estructura de carpetas paso a paso con comandos ejecutables.
- Configuración Python + BD + tests.
- Primer endpoint con observabilidad completa.
- Validación final (checklist).

**Tiempo estimado:** 2–3 horas para tener un proyecto listo.

---

## 📚 Documentación de referencia

### 🎯 Gobierno y operación
- **[GOVERNANCE.md](GOVERNANCE.md)** — Roles RACI, SLA de aprobación, política de Copilot, versionado de contratos
- **[AGENTS.md](AGENTS.md)** — Flujo de tareas, gates de aprobación, Definition of Done
- **[QUICKSTART.md](QUICKSTART.md)** — Onboarding de 5 minutos para desarrollador nuevo

### 🏛️ Técnica y arquitectura
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Reglas arquitectónicas (Hexagonal)
- **[PLANTILLA_INICIO_PROYECTO_LIMPIO_AGENTS_FIRST.md](PLANTILLA_INICIO_PROYECTO_LIMPIO_AGENTS_FIRST.md)** — Guía completa de patrones y principios
- **[docs/adr/](docs/adr/)** — Architecture Decision Records (por qué tomamos ciertas decisiones)

### 🔧 Operación y runbooks
- **[docs/runbooks/](docs/runbooks/)**:
  - `operacion_local.md` — Setup local, troubleshooting
  - `degradacion_controlada.md` — Cómo fallar elegantemente
  - `observabilidad_checklist.md` — Qué es obligatorio en cada endpoint
  - `data_governance.md` — Ciclo de vida de datos, auditoría, autorización
  - `politica_secretos_configuracion.md` — Manejo seguro de credenciales

### 📊 Estado actual del proyecto
- **[PROJECT.md](PROJECT.md)** — Tareas en curso, bloqueos, próximos pasos

---

## 🎯 Flujo típico: evolucionar AgenteLocal

```
1. Lee INSTRUCCIONES_INICIO_PROYECTO.md
   ↓
2. Fase 0–2: Estructura + config (30 min)
   ├─ Naming decisions
   ├─ Crear carpetas hexagonal
   ├─ Setup Python + pyproject.toml
   └─ Copiar plantillas de documentación
   ↓
3. Fase 3–4: Código mínimo válido (1 hora)
   ├─ Health endpoint con trace_id
   ├─ Test del endpoint
   ├─ ADR-0001 (arquitectura)
   └─ Runbooks operacionales
   ↓
4. Fase 5–6: CI + validación (45 min)
   ├─ .gitignore + primer commit
   ├─ GitHub Actions CI
   └─ Checklist final
   ↓
5. Abre PROJECT.md y crea tu primer feature REAL
```

**Total: 2.5–3 horas.**

---

## ⚡ Navegación rápida

| Necesito... | Leo... |
|---|---|
| **Crear proyecto nuevo** | [INSTRUCCIONES_INICIO_PROYECTO.md](INSTRUCCIONES_INICIO_PROYECTO.md) |
| **Entender arquitectura** | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| **Saber quién aprueba qué** | [GOVERNANCE.md](GOVERNANCE.md) § Roles y autoridad (RACI) |
| **Setup local** | [QUICKSTART.md](QUICKSTART.md) |
| **Estado del proyecto** | [PROJECT.md](PROJECT.md) |
| **Troubleshooting** | [docs/runbooks/operacion_local.md](docs/runbooks/operacion_local.md) |
| **Cómo fallar elegantly** | [docs/runbooks/degradacion_controlada.md](docs/runbooks/degradacion_controlada.md) |
| **Observable por defecto** | [docs/runbooks/observabilidad_checklist.md](docs/runbooks/observabilidad_checklist.md) |
| **Datos seguros** | [docs/runbooks/data_governance.md](docs/runbooks/data_governance.md) |
| **Decisiones por qué** | [docs/adr/](docs/adr/) |

---

## 🏗️ Estructura de un proyecto típico (post-inicialización)

```
AgenteLocal - mi_app/
├── .github/
│   ├── copilot-instructions.md       (arquitectura + reglas)
│   └── workflows/
│       └── backend_ci.yml            (lint + tests + security)
│
├── backend/
│   ├── src/mi_app/
│   │   ├── domain/                   (entidades, value objects)
│   │   │   └── __init__.py
│   │   ├── application/              (casos de uso, puertos/interfaces)
│   │   │   ├── ports/
│   │   │   │   └── __init__.py
│   │   │   └── services/
│   │   │       └── __init__.py
│   │   ├── infrastructure/           (adaptadores concretos)
│   │   │   └── persistence/
│   │   │       └── __init__.py
│   │   ├── entrypoints/              (API REST, CLI)
│   │   │   └── api/v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           └── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   └── test_*.py
│   ├── alembic/                      (migraciones BD)
│   │   ├── versions/
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── README.md
│
├── docs/
│   ├── adr/
│   │   ├── ADR-0001-arquitectura-base.md
│   │   └── ADR-000X-*.md
│   ├── runbooks/
│   │   ├── operacion_local.md
│   │   ├── degradacion_controlada.md
│   │   ├── observabilidad_checklist.md
│   │   ├── data_governance.md
│   │   └── politica_secretos_configuracion.md
│   └── checklists/
│       └── coherencia_anti_duplicidad.md
│
├── GOVERNANCE.md                     (roles, SLA, políticas)
├── AGENTS.md                         (operación de agentes IA)
├── QUICKSTART.md                     (onboarding 5 min)
├── PROJECT.md                        (estado ejecutivo)
├── INSTRUCCIONES_INICIO_PROYECTO.md  (guía de inicio)
├── .gitignore
├── .env.example
└── README.md (este archivo)
```

---

## ✨ Principios clave

1. **Arquitectura primero** — Hexagonal/Clean, domain aislado, dependencias hacia adentro.
2. **Evidencia > narrativa** — Todo "DONE" requiere verificación (tests, lint, build).
3. **Fuente canónica única** — No hay reglas duplicadas en múltiples docs.
4. **Cambio mínimo correcto** — Evitar sobreingeniería y refactors innecesarios.
5. **Stop-the-line** — Si falla un gate de aprobación, no se cierra la tarea.

---

## 🔄 Ciclo de vida de un feature típico

```
Feature solicitado ("Project_Correo_AGENT")
    ↓
Understand (req, scope, archivos afectados) — 5 min
    ↓
Inspect (revisar patrón similar existente) — 10 min
    ↓
Plan (pasos, riesgos, verificación) — 10 min
    ↓
Gate (¿requiere pre-aprobación? GOVERNANCE.md RACI) — depende
    ↓
Implement (código mínimo correcto) — 1–4 horas
    ↓
Verify (tests, lint, observabilidad) — 30 min
    ↓
Report (resumen, evidencia, riesgos) — 10 min
    ↓
DONE (con evidencia verificable)
```

---

## 📊 Impacto de esta plantilla

| Aspecto | Mejora |
|---|---|
| **Governance** | ✅ Roles definidos, SLA explícito, escalada clara |
| **Arquitectura** | ✅ Hexagonal desde día 1, defensible |
| **Observabilidad** | ✅ Trace_id obligatorio, métricas por defecto |
| **Seguridad** | ✅ Data governance, auditoría inmutable |
| **DX (Dev Experience)** | ✅ Onboarding 5 min vs. 3 semanas |
| **Escalabilidad** | ✅ Multi-proyecto, patterns reutilizables |

---

## ❓ Preguntas frecuentes

### ¿Qué pasa si el equipo es muy pequeño (1 persona)?
Usa esta plantilla igual. Es un *framework mínimo*, no overhead. Solo simplifica GOVERNANCE.md roles.

### ¿Puedo usar Django en lugar de FastAPI?
No, la guía asume FastAPI. 

### ¿Qué pasa en el primer mes de proyecto?
Semana 1: estructura + health endpoint  
Semana 2: 1 feature real (orden, rate, etc.)  
Semana 3: observabilidad + BD  
Semana 4: CI + secrets policy

### ¿Si no necesito toda esta documentación?
⚠️ **No saltes.** Es inversión inicial (2–3h) que ahorra 10–20h de dolor después.

### ¿Cómo manejo cambios en GOVERNANCE o AGENTS?
ADR nuevo (`docs/adr/ADR-00XX-governance-change-xyz.md`). Nunca cambios sin documentación.

---

## 🚦 Siguientes pasos

1. **Ahora:** Lee [INSTRUCCIONES_INICIO_PROYECTO.md](INSTRUCCIONES_INICIO_PROYECTO.md) (30 min).
2. **Después:** Sigue las fases 0–6 (2.5 horas).
3. **Luego:** Abre [PROJECT.md](PROJECT.md) y comienza tu primer feature.
4. **Cada sprint:** Revisa [docs/checklists/coherencia_anti_duplicidad.md](docs/checklists/coherencia_anti_duplicidad.md).

---

## 📞 Soporte

- **Arquitectura:** Leer [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Operación:** Leer [GOVERNANCE.md](GOVERNANCE.md) § Escalada
- **Código:** Leer [QUICKSTART.md](QUICKSTART.md) § si algo no anda

---

*Plantilla versión 1.0 — Marzo 2026*  
*Responsable: Angel Hidalgo + equipo de arquitectura*
