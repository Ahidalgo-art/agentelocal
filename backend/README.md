# Backend

Esqueleto inicial con Arquitectura Hexagonal.

## Estructura
- `src/agente_local/domain`
- `src/agente_local/application`
- `src/agente_local/infrastructure`
- `src/agente_local/entrypoints`

## Comandos rápidos
```powershell
conda run -n AgenteLocal pip install -e .
alembic upgrade head
conda run -n AgenteLocal python -m uvicorn agente_local.main:app --host 127.0.0.1 --port 8000
```
