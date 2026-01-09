import ctypes
import logging
import os
import platform
import sys

import usb.backend.libusb1

_logger = logging.getLogger(__name__)


def get_dll_path():
    system = platform.system()
    arch, _ = platform.architecture()

    if system != "Windows":
        return None

    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".."),
        )

    dll_name = (
        "libusb-1.0_x64.dll" if arch == "64bit" else "libusb-1.0_x32.dll"
    )

    return os.path.join(base_path, "lib", dll_name)


def load_libusb_backend():
    dll_path = get_dll_path()
    if dll_path and os.path.exists(dll_path):
        try:
            ctypes.CDLL(dll_path)
            _logger.info("Loaded libusb DLL from %s", dll_path)
        except OSError as e:
            _logger.error("Failed to load libusb DLL from %s: %s", dll_path, str(e))
            return None

        return usb.backend.libusb1.get_backend(
            find_library=lambda _: dll_path,
        )

    _logger.info("No DLL needed or file not found. Using system libusb.")
    return usb.backend.libusb1.get_backend()
