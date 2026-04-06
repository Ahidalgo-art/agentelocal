from contextlib import asynccontextmanager

from fastapi import FastAPI

from agente_local.entrypoints.api.v1.router import api_v1_router
from agente_local.infrastructure.persistence.database import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
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
