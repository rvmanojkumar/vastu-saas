import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Increase from default 5
    max_overflow=30,        # Increase from default 10
    pool_timeout=60,        # Increase timeout from 30 to 60 seconds
    pool_pre_ping=True,     # Verify connections before using
    pool_recycle=3600       # Recycle connections after 1 hour
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)