with open('alembic/env.py', 'r') as f:
    content = f.read()

old_section = '# Leer DATABASE_URL de variable de entorno\ndatabase_url = os.environ.get("DATABASE_URL")\nif database_url:\n    config.set_main_option("sqlalchemy.url", database_url)'

new_section = '''# Leer DATABASE_URL de variable de entorno y usar psycopg driver
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Forzar uso de psycopg en lugar de asyncpg para migraciones
    if "asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    config.set_main_option("sqlalchemy.url", database_url)'''

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('alembic/env.py', 'w') as f:
        f.write(content)
    print('✅ env.py actualizado correctamente')
else:
    print('⚠️ Sección no encontrada, intentando actualizar env.py completo...')
    # Crear env.py desde cero
    new_content = '''from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Leer DATABASE_URL de variable de entorno y usar psycopg driver
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Forzar uso de psycopg en lugar de asyncpg para migraciones
    if "asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    with open('alembic/env.py', 'w') as f:
        f.write(new_content)
    print('✅ env.py recreado desde cero')
