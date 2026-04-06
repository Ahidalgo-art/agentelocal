from __future__ import annotations

import asyncio
import os
import sys
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def get_database_url() -> str:
    _load_env_file()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_database_echo() -> bool:
    _load_env_file()
    return os.environ.get("DATABASE_ECHO", "false").strip().lower() == "true"


@lru_cache(maxsize=1)
def create_engine() -> AsyncEngine:
    return create_async_engine(get_database_url(), echo=get_database_echo(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def create_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(create_engine(), expire_on_commit=False)