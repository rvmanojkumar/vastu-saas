import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.numerology_report import NumerologyReport
from app.models.task import Task
from app.models.user import User
from app.services.subscription import check_subscription
from app.services.numerology.calculator import build_chart
from app.tasks.numerology_tasks import generate_numerology_report_task
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/numerology", tags=["Numerology"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class NumerologyGenerateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    date_of_birth: date
    gender: Literal["M", "F", "m", "f"]
    lang: Literal["en", "hi", "mr"] = "en"
    mobile_number: Optional[str] = Field(None, max_length=20)
    report_type: Literal["pdf"] = "pdf"


@router.post("/reports/generate")
def generate_report(
    body: NumerologyGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed, info = check_subscription(db, current_user.id, product="numerology")
    if not allowed:
        raise HTTPException(status_code=403, detail=str(info))

    gender = body.gender.upper()
    chart = build_chart(body.full_name, body.date_of_birth, gender, body.mobile_number)

    task_id = str(uuid.uuid4())
    report = NumerologyReport(
        user_id=current_user.id,
        task_id=task_id,
        full_name=body.full_name.strip(),
        date_of_birth=body.date_of_birth,
        gender=gender,
        mobile_number=body.mobile_number,
        lang=body.lang,
        moolank=chart["moolank"],
        bhagyank=chart["bhagyank"],
        first_name_number=chart["first_name_number"],
        last_name_number=chart["last_name_number"],
        full_name_number=chart["full_name_number"],
        status="pending",
        chart_json=json.dumps(chart),
    )
    db.add(report)
    db.flush()

    task = Task(
        task_id=task_id,
        user_id=current_user.id,
        project_id=None,
        status="PENDING",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(report)

    payload = {
        "full_name": body.full_name.strip(),
        "date_of_birth": body.date_of_birth.isoformat(),
        "gender": gender,
        "lang": body.lang,
        "mobile_number": body.mobile_number,
    }
    generate_numerology_report_task.delay(task_id, report.id, payload)

    return {
        "success": True,
        "task_id": task_id,
        "report_id": report.id,
        "status": "pending",
        "message": "Numerology report generation started",
        "chart_preview": {
            "moolank": chart["moolank"],
            "bhagyank": chart["bhagyank"],
            "zodiac_sign": chart["zodiac_sign"],
        },
    }


@router.get("/reports")
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(NumerologyReport)
        .filter(NumerologyReport.user_id == current_user.id)
        .order_by(NumerologyReport.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "full_name": r.full_name,
            "date_of_birth": r.date_of_birth.isoformat() if r.date_of_birth else None,
            "gender": r.gender,
            "lang": r.lang,
            "moolank": r.moolank,
            "bhagyank": r.bhagyank,
            "status": r.status,
            "result_path": r.result_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/reports/tasks/{task_id}")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == current_user.id).first()
    report = (
        db.query(NumerologyReport)
        .filter(NumerologyReport.task_id == task_id, NumerologyReport.user_id == current_user.id)
        .first()
    )
    if not task and not report:
        raise HTTPException(404, "Task not found")

    status = (task.status if task else report.status or "pending").lower()
    progress = float(task.progress) if task and task.progress is not None else (
        1.0 if status == "completed" else 0.0
    )
    return {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "result_path": (task.result_path if task else None) or (report.result_path if report else None),
        "error": report.error if report else None,
        "created_at": (task.created_at.isoformat() if task and getattr(task, "created_at", None) else None),
    }


@router.get("/preview")
def preview_chart(
    full_name: str,
    date_of_birth: date,
    gender: Literal["M", "F"] = "M",
    mobile_number: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Quick chart calculation without consuming a report credit."""
    return build_chart(full_name, date_of_birth, gender, mobile_number)
