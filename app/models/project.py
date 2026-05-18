# app/models/project.py
from app.db.base import Base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func

import enum

class ProjectStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    BOUNDARY_DRAWN = "boundary_drawn"
    ROOMS_MARKED = "rooms_marked"
    OBJECTS_MARKED = "objects_marked"
    REPORT_GENERATED = "report_generated"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(150))
    client_name = Column(String(255), nullable=True)
    description = Column(Text)
    image_path = Column(String(255), nullable=True) 
    rotation = Column(Integer, default=0)
    starting_degree = Column(Integer, default=0)
    status = Column(String(50), default="uploaded")  # Use String for MySQL compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())