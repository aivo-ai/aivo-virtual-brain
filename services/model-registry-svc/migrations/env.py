"""
AIVO Model Registry - Alembic Environment Configuration
S2-02 Implementation: Database migration environment setup
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import Base
from app.database import db_config

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add model metadata for autogenerate support
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py
# Can be acquired:
# my_important_option = config.get_main_option("my_important_option")


def get_database_url():
    """Get database URL from environment or config"""
    # Use environment configuration
    return db_config.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override the sqlalchemy.url in alembic.ini
    config.set_main_option("sqlalchemy.url", get_database_url())
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Include schemas if needed
            include_schemas=True,
            # Version table configuration
            version_table_schema=None,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
