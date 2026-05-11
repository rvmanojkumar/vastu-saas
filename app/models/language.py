from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True)

    code = Column(String(10), unique=True, nullable=False)

    name = Column(String(50), nullable=False)

    is_active = Column(Boolean, default=True)

    is_default = Column(Boolean, default=False)