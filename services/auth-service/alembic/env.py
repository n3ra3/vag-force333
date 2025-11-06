import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Import target metadata from shared Base
try:
    from shared.database import Base
    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def get_url():
    # Prefer env var DATABASE_URL; alembic expects a sync driver (psycopg2)
    url = os.environ.get('DATABASE_URL')
    if url:
        # If url uses asyncpg (postgresql+asyncpg://) convert to sync URL for Alembic
        if '+asyncpg' in url:
            return url.replace('+asyncpg', '')
        return url
    # fallback to ini
    return config.get_main_option('sqlalchemy.url')


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        # use auth-specific version table
        version_table='alembic_version_auth',
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
            version_table='alembic_version_auth',
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
