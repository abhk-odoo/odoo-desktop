import contextlib
import logging
import time
from queue import Empty, Queue
from threading import Thread

import usb.core
import usb.util
from config.ddl_path import load_libusb_backend
from services.printer_service_base import PrinterServiceBase

_logger = logging.getLogger(__name__)


class UsbPrinterService(PrinterServiceBase):
    """
    ESC/POS printer driver using direct USB (libusb / pyusb).
    Linux-safe implementation.
    """

    EP_OUT = 0x01
    INTERFACE = 0
    TIMEOUT = 5000

    def __init__(self, device_info):
        super().__init__(device_info)

        self.vendor_id = device_info.get("vendor_id")
        self.product_id = device_info.get("product_id")

        self._backend = load_libusb_backend()
        self._device = None

        self._print_job = Queue(maxsize=100)
        self._worker = Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def print_raw(self, data: bytes):
        """Queue raw ESC/POS bytes for USB transmission."""
        self._print_job.put(data)

    def shutdown(self):
        """stop worker thread and release USB device."""
        self._print_job.put(None)
        self._worker.join(timeout=5)

        if self._worker.is_alive():
            _logger.warning("Worker thread did not shutdown cleanly")

        self._release_device()

    def _worker_loop(self):
        while True:
            try:
                data = self._print_job.get(timeout=1)
            except Empty:
                continue

            if data is None:
                self._print_job.task_done()
                break

            try:
                self._send_usb(data)
            except (usb.core.USBError, RuntimeError) as e:
                _logger.error("USB print failed: %s", e)
                self._release_device()
            finally:
                self._print_job.task_done()

    def _get_device(self):
        """
        Find, configure, and claim the USB printer once.
        Linux requires persistent device + interface.
        """
        if self._device:
            return self._device

        dev = usb.core.find(
            idVendor=int(self.vendor_id, 16),
            idProduct=int(self.product_id, 16),
            backend=self._backend,
        )

        if dev is None:
            raise RuntimeError(f"Printer not found (vendor={self.vendor_id}, product={self.product_id})")

        try:
            if dev.is_kernel_driver_active(self.INTERFACE):
                dev.detach_kernel_driver(self.INTERFACE)
        except (usb.core.USBError, NotImplementedError, RuntimeError):
            pass

        dev.set_configuration()
        usb.util.claim_interface(dev, self.INTERFACE)

        self._device = dev
        _logger.info(
            "USB printer connected (vendor=%s, product=%s)",
            self.vendor_id,
            self.product_id,
        )

        return dev

    def _send_usb(self, data: bytes):
        """Send raw ESC/POS bytes."""
        dev = self._get_device()

        dev.write(self.EP_OUT, data, timeout=self.TIMEOUT)

        time.sleep(0.03)

    def _release_device(self):
        """Release USB device on shutdown."""
        if not self._device:
            return

        with contextlib.suppress(usb.core.USBError):
            usb.util.release_interface(self._device, self.INTERFACE)

        with contextlib.suppress(Exception):
            usb.util.dispose_resources(self._device)

        _logger.info(
            "USB printer released (vendor=%s, product=%s)",
            self.vendor_id,
            self.product_id,
        )

        self._device = None

    def _printer_status_content(self):
        title, body = super()._printer_status_content()

        usb_info = (
            f"\nConnection\n"
            f"Type : USB\n"
            f"Vendor ID : {self.vendor_id}\n"
            f"Product ID : {self.product_id}\n"
        ).encode()

        return title, body + usb_info


_printer_services: dict[tuple[str, str], UsbPrinterService] = {}


def get_usb_printer_service(device_info: dict) -> UsbPrinterService:
    """Return a UsbPrinterService instance per physical printer."""
    key = (device_info["vendor_id"], device_info["product_id"])

    service = _printer_services.get(key)
    if service is None:
        service = UsbPrinterService(device_info)
        _printer_services[key] = service

    return service


def shutdown_usb_printer_services():
    """Shutdown all USB printer services."""
    for service in _printer_services.values():
        service.shutdown()

    _printer_services.clear()
