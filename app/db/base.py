from sqlalchemy.orm import declarative_base

Base = declarative_base()

# import models here so Alembic can detect
from app.models import *