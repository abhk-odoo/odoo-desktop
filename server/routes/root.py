from fastapi import APIRouter
from services.printer_service import worker_thread, print_queue

router = APIRouter()

@router.get("/")
def root():
    return {"status": True, "message": "Printer server is running."}

@router.get("/status")
def status():
    return {
        "status": True,
        "server": "running",
        "queue_size": print_queue.qsize(),
        "worker_alive": worker_thread.is_alive(),
    }