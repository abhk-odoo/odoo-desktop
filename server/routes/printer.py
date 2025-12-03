from fastapi import APIRouter
from pydantic import BaseModel
from services.printer_service import print_queue
from services.detection_service import list_known_printers

router = APIRouter()

class PrintRequest(BaseModel):
    receipt: str
    vendor_id: str
    product_id: str
    cash_drawer: bool = False

@router.post("/print")
def print_receipt(data: PrintRequest):
    print_queue.put(data)
    return {"status": True, "message": "Print job queued."}

@router.get("/printer")
def list_printers():
    printers = list_known_printers()
    if printers:
        return {"status": True, "printer": printers[0]}
    return {"status": False, "message": "No printers found"}
