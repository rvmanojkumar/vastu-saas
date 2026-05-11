# app/models/generated_report.py

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    JSON
)

from sqlalchemy.sql import func

from app.db.base import Base


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    language_id = Column(
        Integer,
        ForeignKey("languages.id")
    )

    overall_score = Column(Integer, default=0)

    report_snapshot_json = Column(JSON)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )