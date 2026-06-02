from typing import Dict, Any

from redis import client
from app import db
from app.db.session import SessionLocal
from app.models import Project, User, Room, project, user
from app.models.polygon import Polygon as PolygonModel
from app.services.report.rule_engine import compute_vastu_analysis
import os

def get_report_context(project_id: int, user_id: int, request_data: Dict[str, Any]) -> Dict[str, Any]:

    db = SessionLocal()

    try:
        # ================= CORE ENTITIES =================
        project = db.query(Project).filter(Project.id == project_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        client = {
            "name": getattr(project, "client_name", "") if project else ""
        } if project else None

        analysis_data = compute_vastu_analysis(db, project_id)

        rooms = (db.query(PolygonModel).filter(PolygonModel.project_id == project_id,PolygonModel.type == "room").all())
        chart32 = "file://" + os.path.abspath(f"storage/projects/{project_id}/compass_32.png"
        )

        chart16 = "file://" + os.path.abspath(f"storage/projects/{project_id}/compass_16.png")
        sp_logo_url = "file://" + os.path.abspath("storage/logo.jpg")
        return {
            "project": project,
            "user": user,
            "client": client,
            "rooms": rooms,
            "ratings": analysis_data,
            "chart32": chart32,
            "chart16": chart16,
            "request_data": request_data,
            "sp_logo_url": sp_logo_url
        }

    finally:
        db.close()