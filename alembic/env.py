import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.base import Base
from dotenv import load_dotenv

load_dotenv()

# IMPORT MODELS EXPLICITLY (critical)
import app.models.user
import app.models.subscription
import app.models.plan
import app.models.project
import app.models.room
import app.models.object
import app.models.rule
import app.models.report
import app.models.task
import app.models.language
import app.models.direction
import app.models.report_entity
import app.models.report_rule
import app.models.translation
import app.models.project_object
import app.models.generated_report
import app.models.report_item
import app.models.floorplan
import app.models.polygon


config = context.config

db_url = os.getenv("DATABASE_URL")
db_url = db_url.replace("%", "%%")

config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,   # 🔥 IMPORTANT FIX
            compare_server_default=True  # 🔥 IMPORTANT FIX
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()