# 🚀 Instrucciones de Inicio de Proyecto — Guía Completa

> Para operar y mantener el backend de AgenteLocal siguiendo **Agents First + Arquitectura Hexagonal**.
>
> **Punto de partida:** La carpeta `AgenteLocal/` ya existe y contiene toda la documentación base. Solo necesitas copiarla, personalizar y activar el código.
> **Tiempo estimado:** **2–2.5 horas** en total.

---

## Requisitos previos

Antes de empezar, comprueba que tienes instalado en tu máquina:

- [ ] **Python 3.12+** → `python --version`
- [ ] **Git** → `git --version`
- [ ] **PostgreSQL** local (o acceso a instancia remota)
- [ ] **VS Code** (recomendado) con extensión Python

Si falta algo, instálalo antes de continuar.

---

## FASE 0: Decisiones previas (15 min)

Responde esto antes de copiar la plantilla. Son decisiones que afectan nombre y configuración.

### 1. Nombre del proyecto

- Usar `snake_case` (minúsculas con guion bajo, máximo 3 palabras).
- Debe reflejar el dominio de negocio.

| ✅ Correcto | ❌ Incorrecto |
|---|---|
| `agente_local` | `ProyectoNuevo` (PascalCase) |
| `ordenes_logistica` | `backend_v2_angel_marzo` (largo y vago) |
| `integracion_nacex` | `app` (no específico) |

**Tu decisión:** `NOMBRE_PROYECTO` = _________________

### 2. Roles del equipo

Necesitarás nombres reales para personalizar `GOVERNANCE.md`:

- **Product Owner (PO):** _________________ (quién decide qué se construye)
- **Lead Technical:** _________________ (quién aprueba PRs y diseño)
- **Arquitecto de referencia:** _________________ (quién valida arquitectura)
- **On-call:** _________________ (quién responde si falla en producción)

### 3. Hospedaje inicial

- [ ] Solo local dev (laptop)
- [ ] Staging en servidor compartido (EC2, VPS, Railway…)
- [ ] Producción desde el inicio (AWS, GCP…)

Esto afecta la configuración de `.env` y CI/CD.

### 4. Presupuesto Copilot

- **Importe mensual autorizado:** $_________________ (ej: $150/mes)

Esto va en `GOVERNANCE.md` sección 3.

---

## FASE 1: Copiar y renombrar la plantilla (5 min)

La plantilla `AgenteLocal/` ya tiene toda la estructura y documentación lista.

```powershell
# 1. Navega a tu directorio de proyectos
cd C:\<tu-directorio-de-proyectos>

# 2. Copia la plantilla con el nombre de tu proyecto
Copy-Item -Path "AgenteLocal" -Destination "AgenteLocal - NOMBRE_PROYECTO" -Recurse

# 3. Entra a la copia
cd "AgenteLocal - NOMBRE_PROYECTO"

# 4. Inicializa repositorio git
git init
git config user.name "Tu Nombre"
git config user.email "tu-email@company.com"
```

**Resultado:** Tienes una copia independiente de la plantilla. No toques la carpeta `AgenteLocal/` original — es la plantilla maestra.

---

## FASE 2: Personalizar la documentación (30 min)

La plantilla tiene placeholders que DEBES reemplazar. Usa **buscar y reemplazar** en tu editor (Ctrl+H).

### Qué cambiar y dónde

| Archivo | Placeholder | Reemplazar por |
|---|---|---|
| `GOVERNANCE.md` | `[NAME - Lead Tech]` | Nombre real del Lead Tech |
| `GOVERNANCE.md` | `[NAME - VP Engr]` | Nombre real del aprobador |
| `GOVERNANCE.md` | `[NAME - PM]` | Nombre real del PM |
| `GOVERNANCE.md` | `[NAME - DBA/Lead]` | Nombre real del DBA/Lead |
| `GOVERNANCE.md` | `$[XXX]` | Presupuesto Copilot (ej: `$150`) |
| `PROJECT.md` | `<nombre_proyecto>` | Tu NOMBRE_PROYECTO |
| `PROJECT.md` | `[FECHA]` | Fecha de hoy (ej: `2026-03-18`) |
| `pyproject.toml` | `<nombre-proyecto>` | Tu nombre con guiones (ej: `agente-local`) |
| `pyproject.toml` | `angel@company.com` | Tu email real |
| `.github/copilot-instructions.md` | `<nombre_proyecto>` | Tu NOMBRE_PROYECTO |

### Renombrar la carpeta del módulo Python

```powershell
# La plantilla usa `agente_local` como nombre de ejemplo
# Renómbrala a tu proyecto:
Rename-Item -Path "backend\src\agente_local" -NewName "NOMBRE_PROYECTO"

# Verifica
ls backend\src\
```

### Validar que no quedan placeholders

```powershell
# Estos comandos deben devolver 0 resultados:
Select-String -Path "GOVERNANCE.md" -Pattern "\[NAME"
Select-String -Path "GOVERNANCE.md" -Pattern "\$\[XXX\]"
Select-String -Path "PROJECT.md" -Pattern "<nombre_proyecto>"
Select-String -Recurse -Path "backend" -Pattern "agente_local"
```

Si hay resultados → corrígelos antes de continuar. ✅

---

## FASE 3: Configuración Python (20 min)

### Paso 1: Actualizar cadena de conexión a BD

```powershell
notepad backend\alembic.ini
```

Edita la línea:
```ini
# Antes (plantilla):
sqlalchemy.url = postgresql+psycopg://user:password@localhost/dbname

# Después (tu BD local):
sqlalchemy.url = postgresql+psycopg://TU_USUARIO:TU_PASSWORD@localhost/NOMBRE_PROYECTO_dev
```

> Si usas variables de entorno (recomendado para staging/prod), consulta `docs/runbooks/politica_secretos_configuracion.md`.

### Paso 2: Activar entorno conda e instalar dependencias

```powershell
cd backend

# Activar entorno conda (ya debe estar creado: conda create -n AgenteLocal python=3.12)
conda activate AgenteLocal

# Instalar todas las dependencias
pip install -e ".[dev]"

# Verificar instalación
conda list | Select-String "fastapi|sqlalchemy|pytest|ruff"
```

Output esperado (visible en output conda list):
```
fastapi               0.104.x
sqlalchemy            2.0.x
pytest                7.4.x
ruff                  0.1.x
```

### Paso 3: Crear archivo `.env` local

```powershell
# Crear .env en la raíz de backend/ (NO en raíz del proyecto)
@"
HOST=127.0.0.1
PORT=8000
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=tu_password_local
DB_NAME=NOMBRE_PROYECTO_dev
ENVIRONMENT=development
DEBUG=True
"@ | Out-File -FilePath ".env" -Encoding UTF8

# Comprobar que .gitignore lo excluye
Select-String -Path ".gitignore" -Pattern "^\.env"
```

---

## FASE 4: Verificar el endpoint de salud (20 min)

El template ya incluye `main.py` con `GET /v1/health` y sus tests. Solo necesitas verificar que funcionan correctamente con tu nombre de módulo.

### Paso 1: Ejecutar lint y tests

```powershell
cd backend

# Asegúrate que conda activate AgenteLocal está activo
conda activate AgenteLocal

# Lint (desde carpeta backend/)
ruff check src tests

# Tests
$env:PYTHONPATH = "src"
pytest -v
```

Output esperado:
```
tests/test_health.py::test_health_returns_ok PASSED

1 passed in 0.XXs
```

Si hay `ImportError` → el módulo aún tiene el nombre antiguo. Verifica FASE 2 Paso de renombrado.

### Paso 2: Arrancar la API y probar manualmente

```powershell
# Asegúrate que conda activate AgenteLocal está activo
# Terminal 1: arrancar servidor
python -m uvicorn NOMBRE_PROYECTO.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: llamar al endpoint
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/health | ConvertTo-Json -Depth 5
```

Output esperado:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T14:35:22.123456",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "checks": {
    "database": { "status": "up" },
    "cache": { "status": "up" }
  }
}
```

✅ Si llega respuesta con `trace_id` → API funcionando correctamente.

---

## FASE 5: Git y primer commit (15 min)

### Paso 1: Verificar `.gitignore`

```powershell
# Asegúrate de que estos patrones están presentes:
Select-String -Path ".gitignore" -Pattern "\.env|__pycache__|.coverage"
```

Si falta alguno, añádelo manualmente.

### Paso 2: Commit inicial

```powershell
git add -A

git commit -m "chore: initialize NOMBRE_PROYECTO from hexagonal template

- Renombrar módulo y personalizar documentación
- GOVERNANCE.md con roles del equipo
- PROJECT.md con estado inicial
- health endpoint activo con tests pasando
- .env local configurado (no commiteado)"

git log --oneline
```

### Paso 3: Verificar CI/CD

El template incluye `.github/workflows/backend_ci.yml` con tres gates: lint, tests y seguridad.

```powershell
# Verifica que existe
Test-Path ".github\workflows\backend_ci.yml"
# Debe devolver: True
```

Para activarlo: haz push a GitHub y abre la pestaña **Actions** para confirmar que los tres jobs pasan.

---

## FASE 6: Checklist de validación final (10 min)

Antes de declarar el proyecto como "inicializado y listo para desarrollo":

### ✅ Personalización

- [ ] Sin placeholders en GOVERNANCE.md (`[NAME]`, `$[XXX]`)
- [ ] `PROJECT.md` con nombre real y fecha
- [ ] `pyproject.toml` con nombre, descripción y autor actualizados
- [ ] Carpeta `backend/src/NOMBRE_PROYECTO/` existe con ese nombre

### ✅ Python y entorno

- [ ] `pip install -e ".[dev]"` → sin errores
- [ ] `ruff check src tests` → 0 errores
- [ ] `pytest -v` → 3 tests PASSED
- [ ] API arranca en `127.0.0.1:8000` sin errores
- [ ] `GET /v1/health` → 200 con `trace_id`

### ✅ Git

- [ ] `git status` → directorio limpio
- [ ] `.env` NO aparece en `git status`
- [ ] Primer commit realizado
- [ ] `.github/workflows/backend_ci.yml` presente

### ✅ Documentación

- [ ] `GOVERNANCE.md` tiene nombres reales en RACI
- [ ] `docs/runbooks/` tiene al menos 3 archivos
- [ ] `docs/adr/ADR-0001-arquitectura-base.md` existe
- [ ] `PROJECT.md` sección 2 define próximos pasos

**Si todos ✅:** 🎉 **¡Proyecto inicializado y listo para desarrollo!**

---

## Primeras semanas: plan de trabajo

### Semana 1 — Primera feature real (patrón hexagonal)

Implementa un incremento de correo/calendar definido en `PROJECT_CORREO_AGENT.md` y `docs/specs/SPEC_CORREO_CALENDAR_AGENT_LOCAL.md`.

**Criterios de aceptación:**
- [ ] El dominio no importa FastAPI ni SQLAlchemy
- [ ] Tests del caso de uso pasan sin BD real (inyectando fakes)
- [ ] El incremento mantiene trazabilidad (`trace_id`) y errores API en inglés
- [ ] La tarea implementada coincide con el roadmap de correo/calendar (no ejemplos genéricos de plantilla)

### Semana 2 — Observabilidad completa

- [ ] Logging estructurado JSON en todos los endpoints
- [ ] Prometheus metrics (latencia + contador por endpoint)
- [ ] Health check verifica BD real
- [ ] Referencia: `docs/runbooks/observabilidad_checklist.md`

### Semana 3 — BD y migraciones

- [ ] Primera migración: `alembic revision --autogenerate -m "create_rates_table"`
- [ ] Verificar que `alembic upgrade head` y `alembic downgrade -1` funcionan
- [ ] Documentar en `docs/runbooks/operacion_local.md`

### Semana 4 — CI completo y seguridad

- [ ] GitHub Actions con los 3 jobs passing (lint, test, security)
- [ ] `pip-audit` sin CVE críticos
- [ ] Secrets en GitHub Secrets, no en código
- [ ] Primera aprobación formal usando el flujo de `GOVERNANCE.md`

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'NOMBRE_PROYECTO'` | Carpeta no renombrada o `PYTHONPATH` no configurada | Verifica FASE 2 renombrado; ejecutar desde `backend/` con `$env:PYTHONPATH="src"` |
| `ImportError` en `test_health.py` | Nombre de módulo en import no coincide | Abre `test_health.py` y actualiza `from agente_local` a `from NOMBRE_PROYECTO` |
| `ruff: command not found` | Entorno conda no activo o ruff no instalado | `conda activate AgenteLocal` → `pip install ruff` |
| URI de BD rechazada por alembic | Credenciales incorrectas en `alembic.ini` | Verifica usuario, password, host y nombre de BD |
| `.env` aparece en `git status` | Falta en `.gitignore` | Añadir línea `.env` a `.gitignore` |
| Tests con `ImportError` de `TestClient` | Versión de FastAPI incompatible | Verificar `pip install -e .[dev]` completado correctamente |
| `GOVERNANCE.md` aún tiene `[NAME]` | No se hizo buscar-reemplazar | Usa Ctrl+H en VS Code para reemplazar todos |

---

## Referencias durante el desarrollo

| Necesito saber... | Leo... |
|---|---|
| Cómo estructurar una feature nueva | [QUICKSTART.md](QUICKSTART.md) |
| Quién aprueba mi cambio | [GOVERNANCE.md](GOVERNANCE.md) sección 1 (RACI) |
| Cómo depurar en local | `docs/runbooks/operacion_local.md` |
| Qué hacer si falla una dependencia | `docs/runbooks/degradacion_controlada.md` |
| Qué debe tener cada endpoint | `docs/runbooks/observabilidad_checklist.md` |
| Cómo manejar secretos/credenciales | `docs/runbooks/politica_secretos_configuracion.md` |
| Por qué se tomó decisión arquitectónica X | `docs/adr/` |

---

## Resumen visual del flujo

```
FASE 0  →  Responder 4 decisiones (nombre, roles, hospedaje, presupuesto Copilot) — 15 min
FASE 1  →  Copy-Item "AgenteLocal" + git init — 5 min
FASE 2  →  Buscar/reemplazar placeholders + renombrar módulo — 30 min
FASE 3  →  conda activate + pip install + .env local — 20 min
FASE 4  →  ruff + pytest + uvicorn + GET /v1/health — 20 min
FASE 5  →  git add + commit + verificar CI — 15 min
FASE 6  →  Checklist validación final — 10 min
────────────────────────────────────────────────────
TOTAL:  ~2 horas  →  Proyecto listo para primer feature real
```

---

*Versión 3.0 — 2026-03-18. Basado en copia de plantilla existente.*
*Fuente canónica de este documento: `AgenteLocal/INSTRUCCIONES_INICIO_PROYECTO.md`*

---

## Prompts de trabajo — Gestión de contexto y continuidad

> Copia estos prompts en el chat de Copilot en los momentos indicados.
> Evitan la pérdida de contexto entre sesiones y aseguran que el agente opera
> con la arquitectura y metodología correctas en todo momento.

---

### 1. Prompt de inicio de proyecto (primera sesión)

> Usar la **primera vez** que se trabaja en un proyecto recién inicializado.

```
Iniciamos el trabajo en el proyecto AgenteLocal.

Lee estos archivos en orden antes de actuar:
1. `.github/copilot-instructions.md` — arquitectura hexagonal, política de idioma, reglas de alcance
2. `GOVERNANCE.md` — roles, SLA, gates de aprobación, branching strategy
3. `AGENTS.md` — flujo obligatorio: Understand → Inspect → Plan → Gate → Implement → Verify → Report
4. `PROJECT.md` — estado actual y próximos pasos

Una vez leídos, responde estas tres preguntas antes de actuar:
- ¿Qué capa arquitectónica no puede ser modificada sin aprobación del Lead Tech?
- ¿Cuál es el próximo paso definido en PROJECT.md?
- ¿Qué gate de AGENTS.md aplica al objetivo de hoy?

Objetivo de hoy: Project_Correo_agent.md

No implementes nada hasta haber respondido las tres preguntas y confirmado el plan.
```

---

### 2. Prompt de parada al final de la jornada

> Usar **antes de cerrar VS Code** o finalizar la sesión del día.

```
Vamos a cerrar la sesión de hoy en AgenteLocal.

Antes de parar, necesito que:

1. Resumas qué se ha completado hoy:
   - Archivos modificados (con qué cambio puntual)
   - Tests añadidos o modificados
   - Verificaciones ejecutadas y resultado

2. Describas el estado exacto de lo que está en proceso pero incompleto:
   - Qué falta para que esté DONE según AGENTS.md
   - Si hay algún bloqueo o riesgo identificado

3. Definas el próximo paso concreto para la siguiente sesión:
   - Qué archivo, qué función, qué test
   - Qué decisión está pendiente de tomar

4. Actualices `PROJECT.md` añadiendo esta entrada al final de la sección de bitácora:

## Bitácora — [FECHA HOY]
- **Completado:** [resumen en 2-3 bullets]
- **En proceso:** [qué y por qué está incompleto]
- **Próxima sesión:** [próximo paso exacto — no genérico]
- **Riesgos / deuda:** [si aplica, si no: ninguno]
```

---

### 3. Prompt de reinicio de actividad

> Usar al **comenzar una nueva sesión** en un proyecto en curso (no la primera vez).

```
Retomamos el trabajo en AgenteLocal.

Lee estos archivos y responde antes de actuar:
1. `PROJECT.md` → última entrada de la bitácora: ¿dónde nos quedamos y cuál era el próximo paso?
2. `.github/copilot-instructions.md` → ¿qué capas están permitidas para el cambio de hoy?
3. `AGENTS.md` → ¿qué gate aplica al trabajo pendiente?
4. `PROJECT_CORREO_AGENT.md` y `docs/specs/SPEC_CORREO_CALENDAR_AGENT_LOCAL.md` → ¿el próximo paso está alineado con el alcance correo/calendar?

Una vez leídos, dame este briefing:
- Estado al pausar (1-2 frases)
- Próximo paso exacto pendiente
- Algún riesgo o bloqueo identificado en la sesión anterior

Antes de implementar, añade una validación explícita de alcance:
- "Scope check": confirmar que la tarea pertenece al roadmap de correo/calendar.
- Si aparece un ejemplo genérico de plantilla (p.ej. `rates/import`) y no está en `PROJECT_CORREO_AGENT.md`, no implementarlo.

Luego procede con ese próximo paso siguiendo el flujo de AGENTS.md:
Understand → Inspect → Plan → (Gate si aplica) → Implement → Verify → Report

No saltarte ninguna fase aunque el cambio parezca pequeño.
```

---

### Cuándo usar cada prompt

| Situación | Prompt |
|---|---|
| Primera vez que abres el proyecto | **1 — Inicio de proyecto** |
| Final del día o pausa de más de 4 horas | **2 — Parada al final de jornada** |
| Vuelves después de una pausa | **3 — Reinicio de actividad** |
| Cambias de contexto (otro proyecto → este) | **3 — Reinicio de actividad** |
| Después de una reunión larga sin código | **3 — Reinicio de actividad** |

