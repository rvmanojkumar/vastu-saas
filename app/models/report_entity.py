from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text
)

from app.db.base import Base


class ReportEntity(Base):
    __tablename__ = "report_entities"

    id = Column(Integer, primary_key=True)

    slug = Column(String(100), unique=True, nullable=False)

    category = Column(String(20), nullable=False)
    # room / object

    name = Column(String(100))

    description = Column(Text)

    icon = Column(String(100))

    sort_order = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)