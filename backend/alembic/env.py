from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import app database and config
from app.core.database import Base
from app.core.config import settings

# Import ALL models so Base.metadata is populated
from app.models.profile import Profile  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.analysis import Analysis  # noqa: F401
from app.models.website import Website  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.brand_voice import BrandVoiceConfig, VoiceVector, VoiceRule  # noqa: F401
from app.models.audit_cost import AuditCostLedger  # noqa: F401
from app.models.audit import Audit, AuditStatus  # noqa: F401
from app.models.audit_query import AuditQuery  # noqa: F401
from app.models.engine_response import EngineResponse  # noqa: F401
from app.models.brand_mention import BrandMention  # noqa: F401
from app.models.visibility_score import VisibilityScore  # noqa: F401
from app.models.page_score import PageScore  # noqa: F401
from app.models.criterion_result import CriterionResult  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from app's Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
