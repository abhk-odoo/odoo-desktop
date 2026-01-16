import logging

import usb.core
import usb.util
from config.ddl_path import load_libusb_backend

_logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self, backend=None):
        self.backend = backend or load_libusb_backend()

    def _get_string(self, device, index):
        if not index:
            return None
        try:
            return usb.util.get_string(device, index)
        except usb.core.USBError as e:
            _logger.error(
                "Failed to read USB string descriptor (index=%s): %s",
                index,
                e,
            )
            return None

    def _has_printer_interface(self, device):
        try:
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 0x07:
                        return True
        except usb.core.USBError as e:
            _logger.error(
                "Failed to inspect USB interfaces for device %04x:%04x: %s",
                device.idVendor,
                device.idProduct,
                e,
            )
        return False

    def _get_interfaces(self, device):
        interfaces = []
        try:
            for cfg in device:
                for intf in cfg:
                    for ep in intf:
                        interfaces.append({
                            "interface": intf.bInterfaceNumber,
                            "endpoint": hex(ep.bEndpointAddress),
                            "direction": (
                                "OUT"
                                if usb.util.endpoint_direction(
                                    ep.bEndpointAddress,
                                ) == usb.util.ENDPOINT_OUT
                                else "IN"
                            ),
                            "type": ep.bmAttributes,
                        })
        except usb.core.USBError as e:
            _logger.error(
                "Failed to read endpoints for device %04x:%04x: %s",
                device.idVendor,
                device.idProduct,
                e,
            )
        return interfaces

    def list_printers(self):
        printers = []
        devices = usb.core.find(find_all=True, backend=self.backend)

        for device in devices:
            if not self._has_printer_interface(device):
                continue

            try:
                printers.append({
                    "vendor_id": f"{device.idVendor:04x}",
                    "product_id": f"{device.idProduct:04x}",
                    "manufacturer": (
                        self._get_string(device, device.iManufacturer)
                        or "Unknown"
                    ),
                    "product": (
                        self._get_string(device, device.iProduct)
                        or "Unknown"
                    ),
                    "serial_number": (
                        self._get_string(device, device.iSerialNumber)
                        or "Unknown"
                    ),
                    "bus": device.bus,
                    "address": device.address,
                    "usb_interfaces": self._get_interfaces(device),
                })
            except (AttributeError, ValueError, TypeError) as e:
                _logger.error(
                    "Failed to get info for device: %s",
                    e,
                )

        return printers
