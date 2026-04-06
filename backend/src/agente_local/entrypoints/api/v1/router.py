from fastapi import APIRouter

from agente_local.entrypoints.api.v1.endpoints.accounts import router as accounts_router
from agente_local.entrypoints.api.v1.endpoints.health import router as health_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(accounts_router)
