from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI

from agente_local.entrypoints.api.v1.router import api_v1_router
from agente_local.infrastructure.persistence.database import create_engine


REQUIRED_GOOGLE_ENV_VARS = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
)
_GOOGLE_PLACEHOLDER_VALUES = {
    "",
    "change_me",
    "<tu_client_id>",
    "<tu_client_secret>",
}


def _load_backend_env_file() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _missing_google_env_vars() -> list[str]:
    _load_backend_env_file()
    missing_vars: list[str] = []
    for name in REQUIRED_GOOGLE_ENV_VARS:
        value = os.environ.get(name, "").strip().lower()
        if value in _GOOGLE_PLACEHOLDER_VALUES:
            missing_vars.append(name)
    return missing_vars


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.missing_google_env_vars = _missing_google_env_vars()
    yield
    await create_engine().dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agente Local API",
        version="0.1.0",
        description="Agente de email y calendario — Arquitectura Hexagonal",
        lifespan=lifespan,
    )
    app.include_router(api_v1_router, prefix="/v1")
    return app


app = create_app()
