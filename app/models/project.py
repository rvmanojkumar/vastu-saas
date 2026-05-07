from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String(150))
    description = Column(Text)  # ✅ ADD THIS

    image_path = Column(String(255))

    rotation = Column(Integer, default=0)
    starting_degree = Column(Integer, default=0)