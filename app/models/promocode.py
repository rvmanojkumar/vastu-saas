from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Promocode(Base):
    __tablename__ = "promocodes"
    __table_args__ = (UniqueConstraint("code", name="uq_promocodes_code"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    # percentage | amount
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_usage = Column(Integer, nullable=False, default=1)
    used_count = Column(Integer, nullable=False, default=0)
    ends_on = Column(Date, nullable=False)
    # active | inactive
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    plan = relationship("Plan")
