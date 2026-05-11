from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    JSON
)

from sqlalchemy.sql import func

from app.db.base import Base


class ProjectObject(Base):
    __tablename__ = "project_objects"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    report_entity_id = Column(
        Integer,
        ForeignKey("report_entities.id"),
        nullable=False
    )

    name = Column(String(100))

    coordinates = Column(JSON)

    center_x = Column(Integer)

    center_y = Column(Integer)

    angle = Column(Float)

    direction_16 = Column(String(50))

    direction_32 = Column(String(50))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )