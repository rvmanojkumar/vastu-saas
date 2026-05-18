from typing import Dict, Any

from redis import client
from app import db
from app.db.session import SessionLocal
from app.models import Project, User, Room, project, user
from app.services.report.rule_engine import compute_vastu_analysis

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

        rooms = db.query(Room).filter(Room.project_id == project_id).all()

        return {
            "project": project,
            "user": user,
            "client": client,
            "rooms": rooms,
            "ratings": analysis_data,
            "request_data": request_data
        }

    finally:
        db.close()