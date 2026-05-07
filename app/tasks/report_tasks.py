from app.core.celery_app import celery
from app.services.report.generator import generate_pdf
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.room import Room
from app.models.object import Object
from app.models.task import Task
from app.models.report import Report
from app.core.websocket_manager import manager

import os
import asyncio
import math

def safe_int(value, default=0):
    try:
        if value is None:
            return default

        if isinstance(value, float) and math.isnan(value):
            return default

        return int(value)
    except:
        return default
# =========================
# HELPER: SEND WS UPDATE
# =========================
def send_ws(task_id, payload):
    try:
        asyncio.run(manager.send_update(task_id, payload))
    except Exception as e:
        print("WS ERROR:", e)


# =========================
# HELPER: UPDATE TASK + WS
# =========================
def update_task(db, task, status, progress, task_id, result=None):
    task.status = status
    task.progress = progress

    if result:
        task.result_path = result

    db.commit()

    # 🔥 SEND REAL-TIME UPDATE
    send_ws(task_id, {
        "status": status,
        "progress": progress,
        "result": result
    })


# =========================
# CELERY TASK
# =========================
@celery.task(name="app.tasks.report_tasks.generate_report_task")
def generate_report_task(task_id: str, project_id: int, data: dict):

    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()

        if not task:
            return {"status": "failed", "error": "Task not found"}

        # -------------------------
        # STEP 1: START
        # -------------------------
        update_task(db, task, "PROCESSING", 10, task_id)

        # -------------------------
        # LOAD DATA
        # -------------------------
        project = db.query(Project).filter(Project.id == project_id).first()
        rooms = db.query(Room).filter(Room.project_id == project_id).all()
        objects = db.query(Object).filter(Object.project_id == project_id).all()

        update_task(db, task, "PROCESSING", 30, task_id)

        # -------------------------
        # PREPARE PAYLOAD
        # -------------------------
        payload = {
            "company_name": data.get("company_name"),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "notes": data.get("notes", ""),
            "project_name": project.name if project else "Unknown Project",

            "rooms": [
                {
                    "name": r.name,
                    "direction_16": safe_int(r.direction_16),
                    "direction_32": safe_int(r.direction_32),
                    "result": "good",
                    "color": getattr(r, "color", ""),
                    "therapy": getattr(r, "therapy", "")
                }
                for r in rooms
            ],

            "objects": [
                {
                    "name": o.name,
                    "direction_16": safe_int(o.direction_16),
                    "result": "neutral"
                }
                for o in objects
            ]
        }

        update_task(db, task, "PROCESSING", 60, task_id)

        # -------------------------
        # GENERATE PDF
        # -------------------------
        os.makedirs("storage/reports", exist_ok=True)
        output_file = f"storage/reports/project_{project_id}.pdf"

        generate_pdf(payload, output_file)

        update_task(db, task, "PROCESSING", 90, task_id)

        # -------------------------
        # SAVE REPORT
        # -------------------------
        report = Report(
            project_id=project_id,
            pdf_path=output_file,
            is_whitelabel=False
        )
        db.add(report)

        # -------------------------
        # COMPLETE
        # -------------------------
        update_task(db, task, "COMPLETED", 100, task_id, output_file)

        return {
            "status": "completed",
            "pdf_url": output_file
        }

    except Exception as e:
        if task:
            update_task(db, task, "FAILED", 0, task_id)

        return {
            "status": "failed",
            "error": str(e)
        }

    finally:
        db.close()