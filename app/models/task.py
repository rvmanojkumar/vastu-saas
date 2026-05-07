from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    task_id = Column(String(255), unique=True, index=True)

    user_id = Column(Integer, index=True)
    project_id = Column(Integer, index=True)

    status = Column(String(50), default="PENDING")
    # PENDING | PROCESSING | COMPLETED | FAILED

    progress = Column(Float, default=0.0)

    result_path = Column(String(500), nullable=True)

    error_message = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)