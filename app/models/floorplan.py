from sqlalchemy import Column, Integer, String, JSON, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class ProjectImage(Base):
    __tablename__ = "project_images"
    __table_args__ = {'extend_existing': True}  # ✅ Add this
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

class CanvasState(Base):
    __tablename__ = "canvas_states"
    __table_args__ = {'extend_existing': True}  # ✅ Add this
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    zoom = Column(Float, default=1.0)
    pan_x = Column(Float, default=0.0)
    pan_y = Column(Float, default=0.0)
    rotation = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())