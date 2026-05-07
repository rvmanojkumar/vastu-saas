from fastapi import APIRouter, WebSocket
from app.core.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(task_id)