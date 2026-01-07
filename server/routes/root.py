from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"status": True, "message": "Printer server is running."}
