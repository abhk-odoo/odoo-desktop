import io
import usb.core
import usb.util
import base64
from fastapi import APIRouter
from pydantic import BaseModel
from PIL import Image
from config.ddl_path import load_libusb_backend

router = APIRouter()

class Request(BaseModel):
    image: str
    width: float
    height: float

DPI = 203  # Dots per inch for Zebra printers

def cm_to_pixels(cm: float) -> int:
    px = int((cm / 2.54) * DPI)
    # ZPL requires width multiple of 8
    if px % 8 != 0:
        px -= px % 8
    return px

@router.post("/test-lable")
def test_label(data: Request):
    vid = 0x0A5F
    pid = 0x0187

    width_px = cm_to_pixels(data.width)
    height_px = cm_to_pixels(data.height)

    try:
        img_bytes = base64.b64decode(data.image)
        img = Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        return {"status": False, "message": f"Invalid image base64: {e}"}

    img = img.convert("L")
    img = img.point(lambda x: 255 - x)
    img = img.point(lambda x: 0 if x < 128 else 255, "1")
    img = img.resize((width_px, height_px))

    width_bytes = width_px // 8
    raw_bitmap = img.tobytes()
    total_bytes = len(raw_bitmap)
    hex_data = raw_bitmap.hex().upper()

    zpl = (
        f"^XA\n"
        f"^PW{width_px}\n"
        f"^FO0,0\n"
        f"^GFA,{total_bytes},{total_bytes},{width_bytes},{hex_data}\n"
        f"^XZ\n"
    ).encode("ascii")

    dev = usb.core.find(
        idVendor=vid,
        idProduct=pid,
        backend=load_libusb_backend()
    )

    if dev is None:
        return {"status": False, "message": "Printer not found"}

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass

    try:
        usb.util.claim_interface(dev, 0)
        EP_OUT = 0x01

        dev.write(EP_OUT, b"\x00\x00", timeout=1000)

        dev.write(EP_OUT, zpl, timeout=5000)

    except usb.core.USBError as e:
        return {"status": False, "message": f"USB Error: {e}"}

    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:
            pass

    return { "status": True, "message": "Label printed successfully" }
