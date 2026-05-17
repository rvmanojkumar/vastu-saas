# app/api/reports.py
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from app.db.session import SessionLocal
from app.models.task import Task
from app.models.user import User
from app.models.project import Project
from app.core.security import get_current_user
from app.services.subscription import check_subscription
from app.tasks.report_tasks import generate_report_task
import logging
from fastapi.responses import FileResponse  # Add this import
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])

# ============================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================

class Point(BaseModel):
    x: float = Field(..., ge=0, le=1, description="Normalized X coordinate (0-1)")
    y: float = Field(..., ge=0, le=1, description="Normalized Y coordinate (0-1)")

class CropCenter(BaseModel):
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)

class RoomData(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    center: Point
    direction: str = Field(..., pattern="^(N|NE|E|SE|S|SW|W|NW|NNE|ENE|ESE|SSE|SSW|WSW|WNW|NNW)$")
    # Add other fields as needed

class ReportGenerateRequest(BaseModel):
    # Required fields
    rooms: List[RoomData] = Field(..., min_items=1, description="At least one room required")
    startingDegree: int = Field(..., ge=0, lt=360, description="North direction offset")
    
    # Optional fields with defaults
    imageRotationAngle: int = Field(0, ge=0, lt=360)
    isCropped: bool = False
    cropCenter: Optional[CropCenter] = None
    cropPolygonPoints: Optional[List[Point]] = None
    
    # Company info for whitelabel
    company_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, pattern="^[+]?[0-9\\s-]{10,20}$")
    email: Optional[str] = Field(None, pattern="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")
    logo: Optional[str] = Field(None, description="Base64 encoded logo or URL")
    watermark: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('cropPolygonPoints')
    def validate_crop_polygon(cls, v, values):
        if values.get('isCropped') and not v:
            raise ValueError('cropPolygonPoints required when isCropped is true')
        if v and len(v) < 3:
            raise ValueError('cropPolygonPoints must have at least 3 points')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "rooms": [{"name": "Living Room", "center": {"x": 0.5, "y": 0.5}, "direction": "NE"}],
                "startingDegree": 270,
                "imageRotationAngle": 0,
                "isCropped": False,
                "company_name": "Vastu Solutions",
                "phone": "+1-234-567-8900",
                "email": "info@vastu.com",
                "notes": "Customer wants quick delivery"
            }
        }

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    result_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class ReportGenerateResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    message: str
    project_id: int
    project_name: str

# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# REPORT GENERATION ENDPOINT
# ============================================================

@router.post("/generate/{project_id}", response_model=ReportGenerateResponse)
def generate_report(
    project_id: int, 
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a Vastu compliance report for a project.
    
    This endpoint:
    1. Validates project ownership and subscription
    2. Creates an async task
    3. Returns task ID for status polling
    """
    
    # Log request
    logger.info(f"Report generation requested for project {project_id} by user {current_user.id}")
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        logger.warning(f"Project {project_id} not found or not owned by user {current_user.id}")
        raise HTTPException(
            status_code=404, 
            detail="Project not found or you don't have access"
        )
    
    # Validate project has required data (optional - your task will handle this)
    # This prevents unnecessary task creation
    if not request.rooms:
        raise HTTPException(
            status_code=400,
            detail="At least one room is required to generate a report"
        )
    
    # Subscription check
    allowed, subscription_info = check_subscription(db, current_user.id)
    
    if not allowed:
        logger.warning(f"User {current_user.id} has no active subscription")
        raise HTTPException(
            status_code=403,
            detail=f"Active subscription required. {subscription_info}"
        )
    
    # Create task record
    task_id = str(uuid.uuid4())
    
    task = Task(
        task_id=task_id,
        user_id=current_user.id,
        project_id=project_id,
        status="PENDING",
        progress=0.0
    )
    
    try:
        db.add(task)
        db.commit()
        logger.info(f"Task {task_id} created for project {project_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create report task")
    
    # Prepare data for Celery task
    report_data = request.model_dump(exclude_none=True)
    report_data["project_name"] = project.name
    report_data["user_id"] = current_user.id
    report_data["user_email"] = current_user.email
    
    # Start async task
    try:
        generate_report_task.delay(
            task_id=task_id,
            project_id=project_id,
            data=report_data
        )
        logger.info(f"Celery task {task_id} dispatched")
    except Exception as e:
        # If Celery task fails, update task status
        task.status = "FAILED"
        task.error = str(e)
        db.commit()
        logger.error(f"Failed to dispatch Celery task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start report generation")
    
    return ReportGenerateResponse(
        success=True,
        task_id=task_id,
        status="PENDING",
        message="Report generation started. Use /reports/task/{task_id} to check status.",
        project_id=project_id,
        project_name=project.name
    )

# ============================================================
# TASK STATUS ENDPOINT
# ============================================================

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
@router.get("/task/{task_id}")
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current status of a report generation task"""
    
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Authorization check
    if task.user_id != current_user.id:
        # Admin check (optional)
        is_admin = db.query(User).filter(
            User.id == current_user.id,
            User.is_admin == True
        ).first()
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")
    
    # Prepare response
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "result_path": task.result_path,
        "error": task.error,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }
    
    # 🔥 ADD THIS: If task is completed, find report and add download URL
    if task.status == "COMPLETED" and task.result_path:
        from app.models.report import Report
        report = db.query(Report).filter(Report.pdf_path == task.result_path).first()
        if report:
            response["download_url"] = f"/reports/download/{report.id}"
            response["report_id"] = report.id
    
    return response

# ============================================================
# LIST PROJECT REPORTS
# ============================================================

@router.get("/project/{project_id}")
def get_project_reports(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all reports generated for a project with pagination"""
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    from app.models.report import Report
    
    total = db.query(Report).filter(Report.project_id == project_id).count()
    
    reports = db.query(Report).filter(
        Report.project_id == project_id
    ).order_by(
        Report.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "reports": [
            {
                "id": r.id,
                "pdf_path": r.pdf_path,
                "is_whitelabel": r.is_whitelabel,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "download_url": f"/reports/download/{r.id}"  # Generate download URL
            }
            for r in reports
        ]
    }

# ============================================================
# DOWNLOAD REPORT
# ============================================================

@router.get("/download/{report_id}")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a generated report PDF"""
    
    from app.models.report import Report
    
    # Get report
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Verify access through project
    project = db.query(Project).filter(
        Project.id == report.project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=403, detail="Not authorized to download this report")
    
    # Check if file exists
    if not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Return file for download
    return FileResponse(
        path=report.pdf_path,
        filename=f"vastu_report_project_{report.project_id}.pdf",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=vastu_report_project_{report.project_id}.pdf"
        }
    )