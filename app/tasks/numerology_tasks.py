import json
import logging
import os
import uuid
from datetime import datetime

from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.models.numerology_report import NumerologyReport
from app.models.task import Task
from app.services.numerology.generator import generate_numerology_pdf
from app.services.subscription import increment_usage
from app.core.websocket_manager import manager
import asyncio

logger = logging.getLogger(__name__)


def send_ws(task_id, payload):
    try:
        asyncio.run(manager.send_update(task_id, payload))
    except Exception as e:
        logger.warning(f"WS ERROR: {e}")


@celery.task(name="app.tasks.numerology_tasks.generate_numerology_report_task")
def generate_numerology_report_task(task_id: str, report_id: int, data: dict):
    logger.info(f"Numerology task started: {task_id} report={report_id}")
    db = SessionLocal()
    task = None
    report = None
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        report = db.query(NumerologyReport).filter(NumerologyReport.id == report_id).first()
        if not task or not report:
            return {"status": "failed", "error": "Task or report not found"}

        task.status = "processing"
        task.progress = 0.1
        report.status = "processing"
        db.commit()
        send_ws(task_id, {"status": "processing", "progress": 0.1})

        out_dir = os.path.join("storage", "numerology")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"numerology_{report_id}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = os.path.join(out_dir, filename)

        task.progress = 0.4
        db.commit()
        send_ws(task_id, {"status": "processing", "progress": 0.4})

        # date_of_birth may arrive as ISO string from celery serialization
        from datetime import date as date_cls

        dob = data["date_of_birth"]
        if isinstance(dob, str):
            dob = date_cls.fromisoformat(dob)
        data = {**data, "date_of_birth": dob}

        generate_numerology_pdf(data, file_path)

        task.status = "completed"
        task.progress = 1.0
        task.result_path = file_path
        report.status = "completed"
        report.result_path = file_path
        report.updated_at = datetime.utcnow()
        db.commit()

        increment_usage(db, report.user_id, product="numerology")

        send_ws(task_id, {"status": "completed", "progress": 1.0, "result": file_path})
        return {"status": "completed", "result": file_path}

    except Exception as e:
        logger.exception("Numerology report failed")
        if task:
            task.status = "failed"
            task.progress = 1.0
        if report:
            report.status = "failed"
            report.error = str(e)
        db.commit()
        send_ws(task_id, {"status": "failed", "progress": 1.0, "error": str(e)})
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
