# ⚡ QUICKSTART — 5 minutos para un dev nuevo

No leas todo. Lee esto primero.

---

## 0) Antes de empezar — Comprueba que tienes todo

```powershell
python --version   # Debe ser 3.12.x o superior
git --version      # Cualquier versión reciente
psql --version     # PostgreSQL client disponible
```

Si falta algo:
- Python 3.12: https://python.org/downloads
- Git: https://git-scm.com
- PostgreSQL: https://postgresql.org/download/windows

---

## 1) Entiende la arquitectura (2 min)

El proyecto usa **Hexagonal** (clean architecture):

```
domain/      ← Reglas de negocio puras (sin frameworks)
  ├── entities.py
  ├── value_objects.py
  └── exceptions.py

application/ ← Casos de uso + contratos (interfaces)
  ├── services/
  └── ports/

infrastructure/ ← Adaptadores concretos (BD, APIs externas, etc.)
  └── persistence/

entrypoints/ ← API/CLI que llama al dominio
  └── api/v1/
```

**Regla de oro:** El código SIEMPRE va hacia adentro. Los adaptadores nunca llamam directamente a la API.

---

## 2) Configura el entorno (2 min)

```powershell
# 1. Entra al backend
cd backend

# 1.1 Crea configuración local desde plantilla segura
Copy-Item .env.example .env

# 1.2 Ajusta DATABASE_URL en backend/.env antes de arrancar
# DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/agente_local
# 1.3 Configura Google OAuth para sync (si usaras /v1/sync/{account_id})
# GOOGLE_CLIENT_ID=<tu_client_id>
# GOOGLE_CLIENT_SECRET=<tu_client_secret>
# GOOGLE_PROJECT_ID=<tu_project_id>

# 2. Instala dependencias
conda run -n AgenteLocal pip install -e .

# 3. Valida que funciona
conda run -n AgenteLocal pytest -q

# 4. Levanta la API local
conda run -n AgenteLocal python -m uvicorn agente_local.main:app --host 127.0.0.1 --port 8000

# 5. Testea el health check
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/health | ConvertTo-Json -Depth 5
```

Si todo sale verde → ¡entorno listo!

---

## 3) Entiende el flujo de cambios (1 min)

1. **Entiende** qué necesitas hacer.
2. **Inspecciona** dónde iría el código (revisa estructura similar).
3. **Planeá** el cambio mínimo (no refactorices lo que no se pidió).
4. **Implementá** el cambio.
5. **Verifica** con tests/lint.
6. **Reportá** con evidence (comandos + output).

Esto está en `AGENTS.md` pero eso lo lees después si necesitas detalles.

---

## 4) Revisa qué hay que hacer ahora

Abre `PROJECT.md`:
- ¿Cuál es el sprint actual?
- ¿Cuál es la próxima tarea priorizada?
- ¿Hay bloqueos?

Eso es todo lo que necesitas saber hoy.

---

## 5) Antes de tocar código (checklist de 30 segundos)

- [ ] ¿Mi cambio toca un **endpoint API**? → Necesita aprobación previa (leer `GOVERNANCE.md` sección "Cambio API / Contrato público").
- [ ] ¿Mi cambio toca **DB schema**? → Aprobación previa.
- [ ] ¿Estoy introduciendo dependencia nueva? → Aprobación previa.
- [ ] ¿Es un fix/feature menor en code existente? → No necesita pre-aprobación, solo testa.

---

## 6) Puntos que rompen el build (no hagas esto)

- Tener lógica de negocio en controllers/adaptadores.
- Importar `infrastructure` desde `domain`.
- Hardcodear secretos o URIs en code.
- Dejar tests fallando.
- Commitear sin lint pasando (`ruff check src tests`).

---

## 7) Si algo no anda

1. Revisa `docs/runbooks/operacion_local.md` (problemas comunes).
2. Pregunta en el canal de dev o a Lead Tech.
3. Si es un patrón nuevo que no existe en el code: esto es un ADR → leer `docs/adr/` y proponer.

---

## 8) Eso es todo para hoy

Mañana (si hace falta):
- Leer completo `AGENTS.md` (gobierno más en detalle).
- Leer `GOVERNANCE.md` (quién aprueba qué).
- Leer `.github/copilot-instructions.md` (restricciones de arquitectura).

---

**Next step:** abre `PROJECT.md` y elige tarea. ¡Go!
