from sqlalchemy import Column, Integer, Float, Text, ForeignKey
from app.db.base import Base

class Polygon(Base):
    __tablename__ = "polygons"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    coordinates = Column(Text)

    centroid_x = Column(Float)
    centroid_y = Column(Float)