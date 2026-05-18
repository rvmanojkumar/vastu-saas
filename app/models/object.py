from app.db.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, JSON


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String(100))
    coordinates = Column(JSON)

    center_x = Column(Integer)
    center_y = Column(Integer)

    direction_16 = Column(String(50))
    direction_32 = Column(String(50))