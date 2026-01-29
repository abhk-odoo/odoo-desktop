import socket
from abc import ABC, abstractmethod
from base64 import b64decode
from io import BytesIO

from PIL import Image, ImageOps


class PrinterServiceBase(ABC):
    """
    Abstract Base Class for Printer Service.
    Handles data formatting.
    """

    PRINTER_COMMANDS = {
        'escpos': {
            'center': b'\x1b\x61\x01',  # ESC a n
            'cut': b'\x1d\x56\x41\n',  # GS V m
            'title': b'\x1b\x21\x30%s\x1b\x21\x00',  # ESC ! n
            'drawers': [b'\x1b\x3d\x01', b'\x1b\x70\x00\x19\x19', b'\x1b\x70\x01\x19\x19'],  # ESC = n then ESC p m t1 t2
        },
    }

    def __init__(self, device_info):
        self.device_name = device_info.get('name', 'Unknown')
        self.print_action = device_info.get("action")  # "receipt_printer" or "label_printer"

    def print_receipt(self, data):
        receipt = b64decode(data['receipt'])
        im = Image.open(BytesIO(receipt))

        # Convert to greyscale then to black and white
        im = im.convert("L")
        im = ImageOps.invert(im)
        im = im.convert("1")

        if self.print_action == "receipt_printer":
            payload = b"".join(self.PRINTER_COMMANDS["escpos"]["drawers"]) if data.get("cash_drawer") else b""
            payload += self.format_escpos(im)
        self.print_raw(payload)

    def format_escpos(self, im):
        """ prints with the `GS v 0`-command """
        width = int((im.width + 7) / 8)

        raster_send = b'\x1d\x76\x30\x00'
        max_slice_height = 255

        raster_data = b''
        dots = im.tobytes()
        while len(dots):
            im_slice = dots[:width * max_slice_height]
            slice_height = int(len(im_slice) / width)
            raster_data += raster_send + width.to_bytes(2, 'little') + slice_height.to_bytes(2, 'little') + im_slice
            dots = dots[width * max_slice_height:]

        return self.PRINTER_COMMANDS['escpos']['center'] + raster_data + self.PRINTER_COMMANDS['escpos']['cut']

    def print_status(self):
        """Prints the status ticket of the printer."""
        if self.print_action == "receipt_printer":
            self.print_status_receipt()

    def print_status_receipt(self):
        """Prints the status ticket on the current printer."""
        title, body = self._printer_status_content()
        commands = self.PRINTER_COMMANDS['escpos']

        title = commands['title'] % title
        self.print_raw(commands['center'] + title + b'\n' + body + commands['cut'])

    def _printer_status_content(self):
        """Formats the status information."""
        hostname = socket.gethostname() or "Unknown"
        ip_address = socket.gethostbyname(hostname) or "Unknown"

        title = b'Printer Status'
        body = (
            f"\nPrinter\n"
            f"Printer Name : {self.device_name}\n"
            f"Printer Type : {self.print_action}\n"
            f"\nSystem\n"
            f"Hostname : {hostname}\n"
            f"IP Address : {ip_address}\n"
        ).encode()

        return title, body

    def open_cash_drawer(self):
        """Generates and sends raw bytes to open the cash drawer."""
        if self.print_action != "receipt_printer":
            return

        self.print_raw(b"".join(self.PRINTER_COMMANDS["escpos"]["drawers"]))

    @abstractmethod
    def print_raw(self, data: bytes):
        """Send raw bytes to the hardware."""
        pass
