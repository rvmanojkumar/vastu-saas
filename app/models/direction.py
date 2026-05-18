from app.db.base import Base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float
)
class Direction(Base):
    __tablename__ = "directions"

    id = Column(Integer, primary_key=True)

    code = Column(String(20), unique=True, nullable=False)

    name = Column(String(100))

    system_type = Column(String(10), nullable=False)
    # 16 / 32

    degree_start = Column(Float, nullable=False)

    degree_end = Column(Float, nullable=False)

    sort_order = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)