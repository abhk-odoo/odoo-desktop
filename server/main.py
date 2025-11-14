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
from escpos.printer import Usb
from ddl_path import load_libusb_backend

backend = load_libusb_backend()

# Use backend to find devices
if backend is not None:
    devices = usb.core.find(find_all=True, backend=backend)
    for dev in devices:
        print(f"Found USB device: VID=0x{dev.idVendor:04x}, PID=0x{dev.idProduct:04x}")
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
    """Handles the actual raster print job sent to the ESC/POS printer."""
    printer = None
    try:
        raster_bytes = base64.b64decode(data.raster_base64)
        vendor_id = int(data.vendor_id, 16)
        product_id = int(data.product_id, 16)

        printer = Usb(vendor_id, product_id)

        printer._raw(b'\x1b@')
        bytes_per_row = (data.width + 7) // 8
        header = b'\x1dv0\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([data.height % 256, data.height // 256])
        printer._raw(header + raster_bytes)
        printer._raw(b'\n' * 1) 
        printer.cut()
        if data.cash_drawer:
            printer.cashdraw(2)

    except usb.core.NoBackendError:
        logger.error("[ERROR] USB backend not available. Install libusb driver (use Zadig on Windows). See WINDOWS_USB_SETUP.md")
    except usb.core.USBError as e:
        logger.error(f"[ERROR] USB error during print: {e}. Check if printer is connected and drivers are installed.")
    except Exception as e:
        logger.error(f"[ERROR] Print job error: {e}")
    finally:
        if printer:
            try:
                printer.close()
            except:
                pass

@app.post("/print")
def print_receipt(data: PrintRequest):
    """Enqueues a print job for processing."""
    print_queue.put(data)
    return {"status": True, "message": "Print job queued."}

@app.get("/printer")
def list_usb_printers():
    """Returns the first detected USB ESC/POS printer."""
    try:
        devices = usb.core.find(find_all=True)
    except usb.core.NoBackendError:
        return {
            "status": False,
            "error": "usb_driver_missing",
            "message": "USB driver not found. On Windows, install libusb driver using Zadig. See WINDOWS_USB_SETUP.md for instructions."
        }
    except Exception as e:
        logger.error(f"Error accessing USB devices: {e}")
        return {
            "status": False,
            "error": "usb_access_error",
            "message": f"Failed to access USB devices: {str(e)}"
        }
    
    for device in devices:
        try:
            vendor_id = device.idVendor
            product_id = device.idProduct

            # Optionally skip devices that are not likely printers
            if device.bDeviceClass not in (0, 7):
                continue

            manufacturer = usb.util.get_string(device, device.iManufacturer) or "Unknown"
            product = usb.util.get_string(device, device.iProduct) or "Unknown"

            return {
                "status": True,
                "printer": {
                    "vendor_id": f"{vendor_id:04x}",
                    "product_id": f"{product_id:04x}",
                    "manufacturer": manufacturer,
                    "product": product,
                }
            }

        except usb.core.USBError as e:
            logger.warning(f"USB access error for device: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error getting USB printer info: {e}")
            continue

    return {"status": False, "message": "No USB printers found"}

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