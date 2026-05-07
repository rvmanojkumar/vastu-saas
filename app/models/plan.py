from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    report_limit = Column(Integer, nullable=False)
    is_whitelabel = Column(Boolean, default=False)