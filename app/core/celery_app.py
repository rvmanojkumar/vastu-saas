from celery import Celery

celery = Celery(
    "vastu_saas",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery.conf.imports = [
    "app.tasks.report_tasks"
]