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
from PIL import Image, ImageOps
import io

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
    receipt: str
    vendor_id: str
    product_id: str
    cash_drawer: bool = False

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": True, "message": "Printer server is running."}

def image_to_escpos_raster(img: Image.Image):
    # Convert to 1-bit WITHOUT threshold tweaking
    img = img.convert("L")
    img = ImageOps.invert(img)
    img = img.convert("1")

    width, height = img.size

    if width % 8 != 0:
        padded_width = width + (8 - width % 8)
        padded = Image.new("1", (padded_width, height), 1)
        padded.paste(img, (0, 0))
        img = padded
        width = padded_width

    bytes_per_row = width // 8
    dots = img.tobytes()

    esc = b""
    esc += b"\x1b@"
    esc += b"\x1b\x61\x01"
    esc += b"\x1d\x76\x30\x00"
    esc += bytes([bytes_per_row & 0xFF, bytes_per_row >> 8])
    esc += bytes([height & 0xFF, height >> 8])
    esc += dots
    esc += b"\n\n\n\n"
    esc += b"\x1d\x56\x00"

    return esc

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
        receipt = base64.b64decode(data.receipt)
        im = Image.open(io.BytesIO(receipt))

        esc = image_to_escpos_raster(im)

        if data.cash_drawer:
            esc += b"\x1b\x70\x00\x40\x50"

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

        try:
            dev.set_configuration()
        except Exception as e:
            logger.error(f"set_configuration failed: {e}")

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

def get_string(device, index):
    try:
        return usb.util.get_string(device, index)
    except Exception:
        return None

def list_known_epos_printers():
    devices = usb.core.find(find_all=True, backend=backend)
    printers = []

    for device in devices:
        try:
            vid = device.idVendor
            pid = device.idProduct

            manufacturer = get_string(device, device.iManufacturer) or "Unknown"
            product = get_string(device, device.iProduct) or "Unknown"

            # Detect printer interfaces (ESC/POS or Zebra vendor-interface)
            is_printer_interface = False
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 0x07:
                        is_printer_interface = True
                        break
                if is_printer_interface:
                    break

            # Skip system USB devices
            if is_system_usb_device(manufacturer, product):
                continue

            if not (vid in EPOS_PRINTERS or is_printer_interface):
                continue

            printers.append({
                "vendor_id": f"{vid:04x}",
                "product_id": f"{pid:04x}",
                "manufacturer": manufacturer,
                "vendor_name": EPOS_PRINTERS.get(vid, "Unknown"),
                "product": product,
                "matched_by": (
                    "Vendor id" if vid in EPOS_PRINTERS else
                    "Interface class" if is_printer_interface else
                    "Name keyword"
                ),
                # Add USB interfaces only if detected
                "usb_interfaces": [
                    {
                        "interface": intf.bInterfaceNumber,
                        "endpoint": hex(ep.bEndpointAddress),
                        "direction": (
                            "OUT"
                            if usb.util.endpoint_direction(ep.bEndpointAddress)
                            == usb.util.ENDPOINT_OUT
                            else "IN"
                        ),
                        "type": ep.bmAttributes,
                    }
                    for cfg in device
                    for intf in cfg
                    for ep in intf
                ]
            })

        except Exception as e:
            logger.warning(f"Error reading device info: {e}")

    return printers

@app.get("/printer")
def list_usb_printers():
    """Returns the list of detected printers."""
    printers = list_known_epos_printers()
    if printers:
        return {"status": True, "printer": printers[0]}
    return {"status": False, "message": "No ESC/POS printers found"}

@app.post("/test-lable")
def print_small_barcode():
    """Print ZPL barcode for Zebra ZD421 OEM USB (0a5f:0187)"""
    try:
        vid = 0x0a5f
        pid = 0x0187

        dev = usb.core.find(idVendor=vid, idProduct=pid, backend=load_libusb_backend())
        if dev is None:
            return {"status": False, "message": "Printer not found."}

        # Detach kernel driver
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except:
            pass

        # Claim IF0
        usb.util.claim_interface(dev, 0)

        EP_OUT = 0x01

        # *** REQUIRED FOR ZEBRA RAW USB (wakes channel) ***
        dev.write(EP_OUT, b"\n\n", timeout=1000)

        # *** CLEAN ZPL (NO leading spaces, no indentation) ***
        zpl = (
            b"^XA\n"
            b"^PW254\n"
            b"^LL203\n"
            b"^FO20,20\n"
            b"^BY2,2,40\n"
            b"^BCN,40,Y,N,N\n"
            b"^FD123456789^FS\n"
            b"^FO20,100\n"
            b"^A0N,30,30\n"
            b"^FD123456789^FS\n"
            b"^XZ"
        )

        # *** SEND ZPL BULK WRITE ***
        dev.write(EP_OUT, zpl, timeout=5000)

        # Flush
        dev.write(EP_OUT, b"\n", timeout=1000)

        # Release
        usb.util.release_interface(dev, 0)
        dev.reset()

        return {"status": True, "message": "Barcode printed (RAW USB Bulk Mode)"}

    except Exception as e:
        return {"status": False, "message": str(e)}

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