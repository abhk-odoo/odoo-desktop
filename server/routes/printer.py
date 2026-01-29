from fastapi import APIRouter
from pydantic import BaseModel
from services.detection_service import DetectionService
from services.printer_service_usb import get_usb_printer_service

router = APIRouter()
detector = DetectionService()


class PrintRequest(BaseModel):
    action: str
    printer: dict
    receipt: str = None
    cash_drawer: bool = False


class PrintStatusRequest(BaseModel):
    action: str


class PrinterResponse(BaseModel):
    status: bool
    message: str
    printer: list[dict] = None
    error_code: str = None


@router.post("/print", response_model=PrinterResponse)
def print_receipt(data: PrintRequest):
    printer_data = data.printer or {}
    if not printer_data.get("vendor_id") or not printer_data.get("product_id"):
        return PrinterResponse(
            status=False,
            message="Printer identification is missing",
            error_code="PRINTER_NOT_FOUND",
        )
    printer_data["action"] = data.action
    try:
        printer = get_usb_printer_service(printer_data)

        if data.receipt:
            printer.print_receipt({"receipt": data.receipt})

        if data.cash_drawer:
            printer.open_cash_drawer()

        return PrinterResponse(
            status=True,
            message="Print job queued successfully",
        )
    except RuntimeError as e:
        error_msg = str(e)
        error_code = "PRINT_FAILED"

        if "not found" in error_msg.lower() or "no printers" in error_msg.lower():
            error_code = "PRINTER_NOT_FOUND"
        elif "usb" in error_msg.lower() or "device" in error_msg.lower() or "connection" in error_msg.lower():
            error_code = "CONNECTION_FAILED"

        return PrinterResponse(
            status=False,
            message=f"Failed to print receipt: {error_msg}",
            error_code=error_code,
        )


@router.get("/printer", response_model=PrinterResponse)
def list_printers():
    try:
        printers = detector.list_printers()
        if printers:
            return PrinterResponse(
                status=True,
                message="Printers found",
                printer=printers,
            )

        return PrinterResponse(
            status=False,
            message="No printers available",
            error_code="PRINTER_NOT_FOUND",
        )
    except RuntimeError as e:
        return PrinterResponse(
            status=False,
            message=f"Failed to list printers: {e!s}",
            error_code="CONNECTION_FAILED",
        )


@router.post("/print/status", response_model=PrinterResponse)
def print_printer_status(data: PrintStatusRequest):
    """Print a status ticket for the first available printer."""
    printers = detector.list_printers()

    if not printers or not printers[0]:
        return PrinterResponse(
            status=False,
            message="No printers available",
            error_code="PRINTER_NOT_FOUND",
        )

    printer_info = printers[0]
    printer_info['action'] = data.action

    printer = get_usb_printer_service(printer_info)

    try:
        printer.print_status()
        return PrinterResponse(
            status=True,
            message=f"Status ticket queued for {printer_info['product'] or 'Printer'}",
            printer=[printer_info],
        )
    except RuntimeError as e:
        error_msg = str(e)
        error_code = "PRINT_FAILED"

        # Categorize specific error types
        if "paper" in error_msg.lower() or "roll" in error_msg.lower():
            error_code = "PAPER_OUT"
        elif "cover" in error_msg.lower():
            error_code = "COVER_OPEN"

        return PrinterResponse(
            status=False,
            message=f"Failed to print status ticket: {error_msg}",
            error_code=error_code,
        )
