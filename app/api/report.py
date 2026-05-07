import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.task import Task

from app.tasks.report_tasks import generate_report_task
from app.services.subscription import check_subscription

router = APIRouter(prefix="/reports", tags=["Reports"])


# =========================
# DB Dependency
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# GENERATE REPORT (ASYNC)
# =========================
@router.post("/generate/{project_id}")
def generate_report(project_id: int, data: dict, db: Session = Depends(get_db)):

    """
    Expected payload:
    {
        "user_id": 1,
        "company_name": "...",
        "phone": "...",
        "email": "...",
        "logo": "...",
        "watermark": "...",
        "notes": "..."
    }
    """

    user_id = data["user_id"]

    # -------------------------
    # SUBSCRIPTION CHECK
    # -------------------------
    allowed, sub = check_subscription(db, user_id)

    if not allowed:
        return {
            "success": False,
            "message": sub
        }

    # -------------------------
    # CREATE TASK ID
    # -------------------------
    task_id = str(uuid.uuid4())

    task = Task(
        task_id=task_id,
        user_id=user_id,
        project_id=project_id,
        status="PENDING",
        progress=0.0
    )

    db.add(task)
    db.commit()

    # -------------------------
    # START CELERY TASK (FIXED)
    # -------------------------
    generate_report_task.delay(
        task_id,        # ✅ FIRST
        project_id,     # ✅ SECOND
        data            # ✅ THIRD
    )

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "message": "Report generation started"
    }