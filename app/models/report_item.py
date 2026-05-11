from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from sqlalchemy.sql import func

from app.db.base import Base


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True)

    generated_report_id = Column(
        Integer,
        ForeignKey("generated_reports.id"),
        nullable=False
    )

    project_object_id = Column(
        Integer,
        ForeignKey("project_objects.id"),
        nullable=False
    )

    report_rule_id = Column(
        Integer,
        ForeignKey("report_rules.id"),
        nullable=False
    )

    criticality = Column(String(20))

    score = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )