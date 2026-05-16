from sqlalchemy import Column, Integer, String, JSON, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class PolygonType(str, enum.Enum):
    OUTER_BOUNDARY = "outer_boundary"
    ROOM = "room"
    OBJECT = "object"

class Polygon(Base):
    __tablename__ = "polygons"
    __table_args__ = {'extend_existing': True}  # ✅ Add this
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("polygons.id"), nullable=True)
    type = Column(String(50), nullable=False)
    name = Column(String(100))
    coordinates = Column(JSON, nullable=False)
    centroid = Column(JSON)
    direction = Column(String(20))
    direction_angle = Column(Float)
    color = Column(String(7))
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())