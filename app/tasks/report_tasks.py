from app.core.celery_app import celery
from app.services.report.builder import build_payload
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
import logging

from app.services.report.service import get_report_context

logger = logging.getLogger(__name__)

def safe_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return int(value)
    except:
        return default

def send_ws(task_id, payload):
    try:
        asyncio.run(manager.send_update(task_id, payload))
    except Exception as e:
        print("WS ERROR:", e)

def update_task(db, task, status, progress, task_id, result=None):
    """Update task status and progress"""
    if task is None:
        logger.error(f"Cannot update task {task_id}: task is None")
        return
    
    task.status = status
    task.progress = progress
    if result:
        task.result_path = result
    db.commit()
    
    send_ws(task_id, {
        "status": status,
        "progress": progress,
        "result": result
    })

@celery.task(name="app.tasks.report_tasks.generate_report_task")
def generate_report_task(task_id: str, project_id: int, data: dict):
    
    logger.info(f"========== CELERY TASK STARTED ==========")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Project ID: {project_id}")
    logger.info(f"Data keys: {list(data.keys())}")
    
    db = SessionLocal()
    task = None  # ✅ Initialize task as None
    
    try:
        # Get task from database
        task = db.query(Task).filter(Task.task_id == task_id).first()
        
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"status": "failed", "error": "Task not found"}

        logger.info(f"Task found. Current status: {task.status}")
        
        # Update to PROCESSING
        update_task(db, task, "PROCESSING", 10, task_id)
        logger.info("Task status updated to PROCESSING")

        # Load project
        logger.info(f"Loading project {project_id}")
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            update_task(db, task, "FAILED", 0, task_id)
            return {"status": "failed", "error": f"Project {project_id} not found"}
        
        logger.info(f"Project loaded: {project.name}")
        update_task(db, task, "PROCESSING", 30, task_id)

        # Load rooms
        logger.info("Loading rooms")
        rooms = db.query(Room).filter(Room.project_id == project_id).all()
        logger.info(f"Found {len(rooms)} rooms")
        update_task(db, task, "PROCESSING", 50, task_id)

        # Load objects
        logger.info("Loading objects")
        objects = db.query(Object).filter(Object.project_id == project_id).all()
        logger.info(f"Found {len(objects)} objects")
        update_task(db, task, "PROCESSING", 60, task_id)

        # Prepare payload
        logger.info("Preparing report payload")
        context = get_report_context(
            project_id=project_id,
            user_id=data.get("user_id"),
            request_data=data
        )

        payload = build_payload(context)
        formatted_payload = ' '.join(map(str, payload))
        logger.info(f"Payload prepared with {formatted_payload}")
        update_task(db, task, "PROCESSING", 70, task_id)

        # Generate PDF
        logger.info("Creating storage directory")
        os.makedirs("storage/reports", exist_ok=True)
        output_file = f"storage/reports/project_{project_id}_{task_id}.pdf"
        logger.info(f"Generating PDF: {output_file}")
        generate_pdf(payload, output_file)
        
        # Check if PDF was created
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"PDF generated successfully: {output_file} ({file_size} bytes)")
        else:
            logger.error(f"PDF file was not created: {output_file}")
            raise Exception("PDF generation failed - file not created")
        
        update_task(db, task, "PROCESSING", 90, task_id)

        # Save report record
        logger.info("Saving report record to database")
        report = Report(
            project_id=project_id,
            pdf_path=output_file,
            is_whitelabel=False
        )
        db.add(report)
        db.commit()
        logger.info(f"Report record saved with ID: {report.id}")

        # Complete task
        logger.info("Marking task as COMPLETED")
        update_task(db, task, "COMPLETED", 100, task_id, output_file)
        
        logger.info(f"========== CELERY TASK COMPLETED SUCCESSFULLY ==========")
        
        return {
            "status": "completed",
            "pdf_url": output_file,
            "report_id": report.id
        }

    except Exception as e:
        logger.error(f"========== CELERY TASK FAILED ==========")
        logger.error(f"Error: {str(e)}", exc_info=True)
        
        # ✅ Check if task exists before updating
        if task is not None:
            logger.info(f"Updating task {task_id} status to FAILED")
            try:
                update_task(db, task, "FAILED", 0, task_id)
            except Exception as update_error:
                logger.error(f"Failed to update task status: {update_error}")
        else:
            logger.error(f"Cannot update task {task_id}: task object is None")
            
            # Try to update task directly if task is None
            try:
                task_obj = db.query(Task).filter(Task.task_id == task_id).first()
                if task_obj:
                    task_obj.status = "FAILED"
                    task_obj.error = str(e)
                    db.commit()
                    logger.info(f"Task {task_id} updated to FAILED directly")
            except Exception as direct_update_error:
                logger.error(f"Failed to update task directly: {direct_update_error}")

        return {
            "status": "failed",
            "error": str(e)
        }

    finally:
        logger.info("Closing database session")
        db.close()