# Runbook — Operación local mínima

## Objetivo
Levantar el servicio local y verificar estado saludable.

## Prerrequisitos
- Python 3.12+
- Dependencias instalables desde `backend/`

## Arranque rápido
```powershell
cd backend
python -m pip install -e .
alembic upgrade head
python -m uvicorn <app>.main:app --host 127.0.0.1 --port 8000
```

## Verificación
```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/health | ConvertTo-Json -Depth 5
```

## Diagnóstico básico
1. Si falla `alembic`: revisar `DATABASE_URL` y `ALEMBIC_VERSION_TABLE`.
2. Si falla arranque API: revisar imports, variables de entorno y puerto ocupado.
3. Si falla health: revisar logs de arranque y rutas registradas.

## Evidencia mínima en soporte/incidencia
- Comandos ejecutados.
- Resultado de health.
- Último bloque de logs relevante.
