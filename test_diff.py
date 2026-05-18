import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata

from app.db.base import Base

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    # 🔥 THIS IS THE CORRECT CONTEXT
    mc = MigrationContext.configure(conn)

    diff = compare_metadata(mc, Base.metadata)

    print(diff)