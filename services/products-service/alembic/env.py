import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config
fileConfig(config.config_file_name)

try:
    from shared.database import Base
    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def get_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        if '+asyncpg' in url:
            return url.replace('+asyncpg', '')
        return url
    return config.get_main_option('sqlalchemy.url')


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        # Use a service-specific version table to avoid conflicts when multiple
        # services share the same database. This keeps migration history per-service.
        version_table='alembic_version_products',
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # per-service version table name
            version_table='alembic_version_products',
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
