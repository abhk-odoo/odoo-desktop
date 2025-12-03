from PIL import Image, ImageOps

def image_to_escpos_raster(img: Image.Image):
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
