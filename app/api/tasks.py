from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.task import Task

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# GET TASK STATUS
# =========================
@router.get("/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):

    """
    Returns:
    - status (PENDING / PROCESSING / COMPLETED / FAILED)
    - progress (0 - 100)
    - result file path (if completed)
    """

    task = db.query(Task).filter(Task.task_id == task_id).first()

    if not task:
        return {
            "success": False,
            "message": "Task not found"
        }

    return {
        "success": True,
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "result": task.result_path
    }


# =========================
# LIST USER TASKS (OPTIONAL BUT USEFUL)
# =========================
@router.get("/user/{user_id}")
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):

    tasks = db.query(Task).filter(Task.user_id == user_id).all()

    return {
        "success": True,
        "tasks": [
            {
                "task_id": t.task_id,
                "project_id": t.project_id,
                "status": t.status,
                "progress": t.progress,
                "result": t.result_path
            }
            for t in tasks
        ]
    }