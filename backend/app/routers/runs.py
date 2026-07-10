import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.docker_runner import run_test
from app.models import Run, Test
from app.schemas import RunOut
from app.ws_manager import ws_manager

router = APIRouter(tags=["runs"])


@router.post("/api/tests/{test_id}/run", response_model=RunOut)
async def trigger_run(test_id: str, db: Session = Depends(get_db)):
    test = db.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    run = Run(test_id=test_id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Fire and forget: the run progresses in the background and reports
    # itself via WebSocket + polling the run's status.
    asyncio.create_task(run_test(run.id, test_id))

    return run


@router.get("/api/runs", response_model=list[RunOut])
def list_runs(test_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Run)
    if test_id:
        q = q.filter(Run.test_id == test_id)
    return q.order_by(desc(Run.created_at)).limit(100).all()


@router.get("/api/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.websocket("/ws/runs/{run_id}")
async def run_socket(websocket: WebSocket, run_id: str):
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            # We only push from the server side; just keep the connection
            # alive and drop it if the client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(run_id, websocket)



@router.get("/health")
async def health():
    return {"status": "ok"}