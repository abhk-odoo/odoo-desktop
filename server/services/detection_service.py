import usb.core
import usb.util
from config.ddl_path import load_libusb_backend

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
    "generic usb hub", "apple", "usb host controller", "usb high-speed bus"
}

def get_string(dev, idx):
    try:
        return usb.util.get_string(dev, idx)
    except:
        return None

def is_system_usb_device(manufacturer, product):
    m = manufacturer.lower()
    p = product.lower()
    return any(k in m or k in p for k in SYSTEM_USB_KEYWORDS)

def list_known_printers():
    devices = usb.core.find(find_all=True, backend=load_libusb_backend())
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
            print(f"Error reading device info: {e}")

    return printers
