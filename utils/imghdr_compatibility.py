"""
A compatibility module to replace the deprecated imghdr module with PIL-based functionality.
"""
from PIL import Image
import io
import sys
import os

# Dictionary mapping PIL formats to file extensions
FORMAT_TO_EXTENSION = {
    'JPEG': 'jpeg',
    'PNG': 'png',
    'GIF': 'gif',
    'BMP': 'bmp',
    'TIFF': 'tiff',
    'WEBP': 'webp',
    'ICO': 'ico'
}

def what(file, h=None):
    """
    Determine the type of image contained in a file or memory buffer.
    
    Args:
        file: A filename (string), pathlib.Path object, or a file object open in binary mode.
        h: A bytes object containing the header of the file (ignored, for compatibility).
        
    Returns:
        A string describing the image type (e.g., 'png', 'jpeg', etc.) or None if the type cannot be determined.
    """
    try:
        if isinstance(file, (str, os.PathLike)):
            with Image.open(file) as img:
                format = img.format
        elif hasattr(file, 'read'):
            # If it's a file-like object
            position = file.tell()
            try:
                with Image.open(file) as img:
                    format = img.format
            finally:
                file.seek(position)  # Reset file position
        elif isinstance(file, bytes):
            # If it's bytes data
            with Image.open(io.BytesIO(file)) as img:
                format = img.format
        else:
            return None
            
        # Convert PIL format to imghdr-style extension
        return FORMAT_TO_EXTENSION.get(format, None)
    except Exception:
        return None

# Make the module appear as if it were imghdr
sys.modules['imghdr'] = sys.modules[__name__]

# For testing/debugging
if __name__ == "__main__":
    import os
    for filename in os.listdir("."):
        if os.path.isfile(filename):
            img_type = what(filename)
            if img_type:
                print(f"{filename}: {img_type}")
