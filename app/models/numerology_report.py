from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey
from app.db.base import Base


class NumerologyReport(Base):
    __tablename__ = "numerology_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)

    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(1), nullable=False)  # M / F
    mobile_number = Column(String(20), nullable=True)
    lang = Column(String(5), default="en")

    # Core calculated numbers (denormalized for list views)
    moolank = Column(Integer, nullable=True)
    bhagyank = Column(Integer, nullable=True)
    first_name_number = Column(Integer, nullable=True)
    last_name_number = Column(Integer, nullable=True)
    full_name_number = Column(Integer, nullable=True)

    status = Column(String(30), default="pending")
    result_path = Column(String(500), nullable=True)
    error = Column(Text, nullable=True)
    chart_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
