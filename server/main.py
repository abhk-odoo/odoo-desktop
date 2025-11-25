# -*- coding: utf-8 -*-
import base64
import usb.core
import usb.util
import sys
import atexit
import logging
from queue import Queue
from threading import Thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ddl_path import load_libusb_backend

backend = load_libusb_backend()

# Use backend to find devices
if backend is not None:
    devices = usb.core.find(find_all=True, backend=backend)
else:
    print("[ERROR] libusb backend could not be initialized.")

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("print-server")

# ========== App Setup ==========
app = FastAPI(
    title="Local Print Agent API",
    description="A FastAPI server to communicate with ESC/POS thermal printers over USB.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PrintRequest(BaseModel):
    """Model for receiving raster print job data."""
    raster_base64: str
    width: int
    height: int
    vendor_id: str
    product_id: str
    cash_drawer: bool = False

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": True, "message": "Printer server is running."}

print_queue = Queue(maxsize=100)

def printer_worker():
    """Worker thread that continuously processes print jobs."""
    while True:
        data = print_queue.get()
        if data is None:
            break
        try:
            handle_print_job(data)
        except Exception as e:
            logger.error(f"[ERROR] Print job failed: {e}")
        finally:
            print_queue.task_done()

def handle_print_job(data: PrintRequest):
    """Handles the raster print job using direct USB write (Epson style)."""
    try:
        # Decode raster image
        raster_bytes = base64.b64decode(data.raster_base64)

        width = data.width
        height = data.height

        if width % 8 != 0:
            width += 8 - (width % 8)

        bytes_per_row = width // 8

        esc = b"\x1b@"

        esc += b"\x1b\x61\x01"

        left_margin = 40  # adjust if needed
        esc += b"\x1b\x6c" + bytes([
            left_margin & 0xFF,
            (left_margin >> 8) & 0xFF
        ])

        header = (
            b"\x1d\x76\x30\x00"
            + bytes([bytes_per_row & 0xFF, (bytes_per_row >> 8) & 0xFF])
            + bytes([height & 0xFF, (height >> 8) & 0xFF])
        )

        esc += header + raster_bytes

        # ---- Add bottom padding ----
        BOTTOM_PADDING = 200  # pixels
        empty_row = b"\x00" * bytes_per_row
        esc += empty_row * BOTTOM_PADDING

        # ---- Cut paper ----
        esc += b"\n"
        esc += b"\x1dV\x00"  # full cut

        # ---- Cash drawer (optional) ----
        if data.cash_drawer:
            esc += b"\x1bp\x02\x40\x50"

        # ---- Locate printer ----
        vendor_id = int(data.vendor_id, 16)
        product_id = int(data.product_id, 16)

        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=load_libusb_backend())
        if dev is None:
            raise Exception("Printer not found.")

        # ---- Detach kernel driver (Linux) ----
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except Exception:
            pass

        usb.util.claim_interface(dev, 0)

        EP_OUT = 0x01  # most thermal printers use endpoint 1

        dev.write(EP_OUT, esc, timeout=5000)

        # ---- Cleanup ----
        usb.util.release_interface(dev, 0)
        dev.reset()

    except Exception as e:
        logger.error(f"[ERROR] Print job error: {e}")

@app.post("/print")
def print_receipt(data: PrintRequest):
    """Enqueues a print job for processing."""
    print_queue.put(data)
    return {"status": True, "message": "Print job queued."}

EPOS_PRINTERS = {
    0x4b43: "Caysn",
    0x0fe6: "RuGtek or Xprinter",
    0x04b8: "EPSON",
    0x1504: "BIXOLON",
    0x0416: "Winbond",
    0x1fc9: "POSBANK",
    0x0519: "Star Micronics",
}

SYSTEM_USB_KEYWORDS = {
    "linux", "xhci-hcd", "ehci-hcd", "root hub", "usb hub",
    "microsoft", "standard usb host controller", "usb root hub",
    "generic usb hub",
    "apple", "usb host controller", "usb high-speed bus"
}

KEYWORDS = ["printer", "thermal", "receipt", "pos", "rugtek", "xprinter"]

def is_system_usb_device(manufacturer, product):
    m = manufacturer.lower()
    p = product.lower()
    return any(k in m or k in p for k in SYSTEM_USB_KEYWORDS)

def list_known_epos_printers(known=True):
    devices = usb.core.find(find_all=True)
    printers = []

    for device in devices:
        try:
            vid = device.idVendor
            pid = device.idProduct

            is_known_vendor = vid in EPOS_PRINTERS
            is_printer_interface = False

            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 0x07:
                        is_printer_interface = True
                        break
                if is_printer_interface:
                    break

            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"
            name_combined = f"{manufacturer} {product}".lower()

            if is_system_usb_device(manufacturer, product):
                continue

            has_keyword_match = any(keyword in name_combined for keyword in KEYWORDS)

            if known and not is_known_vendor:
                continue
            elif known and not (is_known_vendor or is_printer_interface or has_keyword_match):
                continue

            printers.append({
                "vendor_id": f"{vid:04x}",
                "product_id": f"{pid:04x}",
                "manufacturer": manufacturer,
                "vendor_name": EPOS_PRINTERS.get(vid, "Unknown"),
                "product": product,
                "matched_by": (
                    "No Filter Applied" if known == False else
                    "Vendor id" if is_known_vendor else
                    "Interface class" if is_printer_interface else
                    "Name keyword"
                ),
            })

        except Exception as e:
            logger.warning(f"Error reading device info: {e}")
            continue

    return printers

@app.get("/printer")
def list_usb_printers():
    """Returns the list of detected printers."""
    printers = list_known_epos_printers(known=True)
    if printers:
        return {"status": True, "printer": printers[0]}
    return {"status": False, "message": "No ESC/POS printers found"}

worker_thread = Thread(target=printer_worker, daemon=True)
worker_thread.start()

def shutdown():
    """Cleanly shuts down the worker thread."""
    print_queue.put(None)
    worker_thread.join()

if __name__ == "__main__":
    import uvicorn
    atexit.register(shutdown)
    port = 5050
    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)