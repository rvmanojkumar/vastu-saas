from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    UniqueConstraint
)

from sqlalchemy.sql import func

from app.db.base import Base


class ReportRule(Base):
    __tablename__ = "report_rules"

    id = Column(Integer, primary_key=True)

    report_entity_id = Column(
        Integer,
        ForeignKey("report_entities.id"),
        nullable=False
    )

    direction_id = Column(
        Integer,
        ForeignKey("directions.id"),
        nullable=False
    )

    criticality = Column(String(20), nullable=False)
    # excellent / good / average / bad / critical

    severity_color = Column(String(20))

    score = Column(Integer, default=0)

    priority = Column(Integer, default=1)

    recommendation_priority = Column(Integer, default=1)

    is_premium = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            'report_entity_id',
            'direction_id',
            name='uq_report_entity_direction'
        ),
    )