import base64
import usb.core
import usb.util
import io
from threading import Thread
from queue import Queue
from services.raster_service import image_to_escpos_raster
from config.ddl_path import load_libusb_backend
from PIL import Image

print_queue = Queue(maxsize=100)

def handle_print_job(data):
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
            print(f"set_configuration failed: {e}")

        usb.util.claim_interface(dev, 0)

        EP_OUT = 0x01  # most thermal printers use endpoint 1

        dev.write(EP_OUT, esc, timeout=5000)

        # ---- Cleanup ----
        usb.util.release_interface(dev, 0)
        dev.reset()

    except Exception as e:
        print(f"[ERROR] Print job error: {e}")

def worker():
    while True:
        item = print_queue.get()
        if item is None:
            break
        handle_print_job(item)
        print_queue.task_done()

worker_thread = Thread(target=worker, daemon=True)
worker_thread.start()

def printer_shutdown():
    print_queue.put(None)
    worker_thread.join()
