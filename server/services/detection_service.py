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

    def _detect_device_type(self, device):
        """Detect the device type which is connected to System."""
        try:
            for cfg in device:
                for intf in cfg:
                    if intf.bInterfaceClass == 0x07:
                        return "printer"
        except usb.core.USBError as e:
            _logger.error(
                "Failed to detect device type for device %04x:%04x: %s",
                device.idVendor,
                device.idProduct,
                e,
            )
        return None

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

    def _normalize_printer_names(self, devices):
        """
        Add a unique, user-friendly display_name for each printer.
        Example: TM-T82, TM-T82 (2), Printer, Printer (2)
        """
        seen = {}

        for device in devices:
            if device.get("device_type") != "printer":
                continue

            product = (device.get("product") or "").strip()
            base_name = product if product and product != "Unknown" else "Printer"

            key = (device["vendor_id"], device["product_id"], base_name)

            seen[key] = seen.get(key, 0) + 1
            device["display_name"] = (
                f"{base_name} ({seen[key]})"
                if seen[key] > 1
                else base_name
            )

    def list_devices(self):
        devices_info = []
        devices = usb.core.find(find_all=True, backend=self.backend)

        for device in devices:
            device_type = self._detect_device_type(device)
            if not device_type:
                continue

            try:
                devices_info.append({
                    "product": (
                        self._get_string(device, device.iProduct)
                        or "Unknown"
                    ),
                    "manufacturer": (
                        self._get_string(device, device.iManufacturer)
                        or "Unknown"
                    ),
                    "device_type": device_type,
                    "vendor_id": f"{device.idVendor:04x}",
                    "product_id": f"{device.idProduct:04x}",
                    "serial_number": self._get_string(device, device.iSerialNumber),
                    "bus": device.bus,
                    "address": device.address,
                    "usb_interfaces": self._get_interfaces(device),
                })
            except (AttributeError, ValueError, TypeError) as e:
                _logger.error(
                    "Failed to get info for device: %s",
                    e,
                )

        self._normalize_printer_names(devices_info)
        return devices_info
