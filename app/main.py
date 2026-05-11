from fastapi import FastAPI
from app.api.room import router as room_router
from app.api.object import router as object_router
from app.api.rules import router as rule_router
from app.api.project import router as project_router
from app.api.report import router as report_router
from app.api.tasks import router as tasks_router
from app.api.auth import router as auth_router  # ADD THIS
from app.api.subscriptions import router as subscription_router  # ADD THIS
from app.db.session import SessionLocal
from app.db.seed import seed
from app.api.ws import router as ws_router
from fastapi.staticfiles import StaticFiles
from app.api.payment import router as payment_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(room_router)
app.include_router(rule_router)
app.include_router(auth_router)  # ADD THIS - Authentication
app.include_router(subscription_router)  # ADD THIS - Subscription management
app.include_router(payment_router)
app.include_router(object_router)
app.include_router(project_router)
app.include_router(report_router)
app.include_router(ws_router)
app.include_router(tasks_router)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

@app.get("/")
def root():
    return {
        "message": "Vastu SaaS API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "subscriptions": "/api/subscriptions",
            "projects": "/projects",
            "reports": "/reports"
        }
    }