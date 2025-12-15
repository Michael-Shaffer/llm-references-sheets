from pathlib import Path
import pymupdf as fitz
import pdfplumber
import multiprocessing
from PIL import Image

def get_color_name(color: int) -> str:
    """Returns the name of the closest color to the given"""

    if color is None:
        return "No Color"

    # Extract the RGB Components from the integer
    red = (color >> 16) & 0xFF
    green = (color >> 8) & 0xFF
    blue = color & 0xFF

    rgb_tuple1 = (red, green, blue)

    colors = {
        "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
        "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
        "white": (255, 255, 255), "black": (0, 0, 0), "gray": (128, 128, 128),
        "maroon": (128, 0, 0), "navy": (0, 0, 128), "olive": (128, 128, 0),
        "teal": (0, 128, 128), "purple": (128, 0, 128), "aquamarine": (127, 255, 212),
        "lime": (0, 255, 0), "silver": (192, 192, 192)
    }

    min_distance = float('inf')
    closest_color_name = "unknown"
    r1, g1, b1 = rgb_tuple1
    for name, rgb_tuple2 in colors.items():
        r2, g2, b2 = rgb_tuple2
        squared_distance = (r2 - r1)**2 + (g2 - g1)**2 + (b2 - b1)**2
        if squared_distance < min_distance:
            min_distance = squared_distance
            closest_color_name = name
    return closest_color_name
