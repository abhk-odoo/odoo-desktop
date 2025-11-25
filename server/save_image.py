import os
from PIL import Image
import base64
import datetime

def save_receipt_as_image(data, image_filename: str = None) -> str:
    """Save receipt raster data as PNG image for testing.
    Returns the file path where image was saved."""
    
    # Decode raster image
    raster_bytes = base64.b64decode(data.raster_base64)

    width = data.width
    height = data.height

    if width % 8 != 0:
        width += 8 - (width % 8)

    bytes_per_row = width // 8

    # Convert raster data to image
    img = Image.new('1', (width, height), 1)  # 1-bit pixels, initially white
    pixels = img.load()
    
    # Convert the raster bytes to pixel data
    for y in range(height):
        row_start = y * bytes_per_row
        for x in range(width):
            byte_index = x // 8
            bit_index = 7 - (x % 8)  # Most significant bit first
            if row_start + byte_index < len(raster_bytes):
                byte_val = raster_bytes[row_start + byte_index]
                pixel_val = (byte_val >> bit_index) & 1
                pixels[x, y] = 0 if pixel_val else 1  # Invert: 0=black, 1=white
    
    # Add bottom padding to the image
    BOTTOM_PADDING = 200
    total_height = height + BOTTOM_PADDING
    full_img = Image.new('1', (width, total_height), 1)
    full_img.paste(img, (0, 0))
    
    # Generate filename if not provided
    if image_filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"receipt_{timestamp}.png"
    
    # Ensure it's saved in the same directory as main.py
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_filename)
    full_img.save(filepath, "PNG")
    
    return filepath

def save_escpos_as_image(esc_data: bytes, image_filename: str = None):
    """Correctly extract and save ESC/POS raster image from GS v 0 command."""

    RASTER_CMD = b"\x1d\x76\x30"
    pos = esc_data.find(RASTER_CMD)
    if pos < 0:
        raise ValueError("GS v 0 raster command not found")

    # m parameter = esc_data[pos+3]
    mode = esc_data[pos + 3]

    # bytes_per_row = xL + 256*xH
    xL = esc_data[pos + 4]
    xH = esc_data[pos + 5]
    bytes_per_row = xL + (xH << 8)

    # height = yL + 256*yH
    yL = esc_data[pos + 6]
    yH = esc_data[pos + 7]
    height = yL + (yH << 8)

    # DATA START
    raster_start = pos + 8
    data_length = bytes_per_row * height

    raster_bytes = esc_data[raster_start:raster_start + data_length]

    # WIDTH = bytes_per_row * 8
    width = bytes_per_row * 8

    # Create image
    img = Image.new("1", (width, height), 1)
    pixels = img.load()

    # Convert ESC/POS raster -> bitmap
    index = 0
    for y in range(height):
        for byte_i in range(bytes_per_row):
            byte_val = raster_bytes[index]
            index += 1
            for bit in range(8):
                x = byte_i * 8 + (7 - bit)
                pixels[x, y] = 0 if (byte_val >> bit) & 1 else 1

    # Save file
    if image_filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"escpos_dump_{timestamp}.png"

    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_filename)
    img.save(filepath, "PNG")
    return filepath