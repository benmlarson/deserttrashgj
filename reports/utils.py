import time
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

TEMP_PHOTO_DIR = Path(settings.MEDIA_ROOT) / "tmp_uploads"
TEMP_MAX_AGE = 30 * 60  # 30 minutes in seconds


def cleanup_temp_uploads():
    """Delete files in tmp_uploads older than 30 minutes."""
    if not TEMP_PHOTO_DIR.is_dir():
        return
    cutoff = time.time() - TEMP_MAX_AGE
    for path in TEMP_PHOTO_DIR.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def extract_gps_from_exif(image_file):
    """Extract GPS coordinates from EXIF data in an image file.

    Returns ((lat, lng), exif_dict) or (None, exif_dict).
    On any failure returns (None, None).
    """
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        exif_data = img._getexif()
        if not exif_data:
            image_file.seek(0)
            return None, None

        # Tag 34853 = GPSInfo
        gps_info = exif_data.get(34853)
        if not gps_info:
            image_file.seek(0)
            return None, _serialize_exif(exif_data)

        def dms_to_decimal(dms, ref):
            degrees = float(dms[0])
            minutes = float(dms[1])
            seconds = float(dms[2])
            decimal = degrees + minutes / 60.0 + seconds / 3600.0
            if ref in ("S", "W"):
                decimal = -decimal
            return decimal

        # GPSLatitude = tag 2, GPSLatitudeRef = tag 1
        # GPSLongitude = tag 4, GPSLongitudeRef = tag 3
        if 2 in gps_info and 1 in gps_info and 4 in gps_info and 3 in gps_info:
            lat = dms_to_decimal(gps_info[2], gps_info[1])
            lng = dms_to_decimal(gps_info[4], gps_info[3])
            image_file.seek(0)
            return (lat, lng), _serialize_exif(exif_data)

        image_file.seek(0)
        return None, _serialize_exif(exif_data)
    except Exception:
        try:
            image_file.seek(0)
        except Exception:
            pass
        return None, None


def _serialize_exif(exif_data):
    """Convert EXIF data to a JSON-serializable dict."""
    from PIL.ExifTags import TAGS

    result = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        try:
            # Skip binary/bytes data and complex objects
            if isinstance(value, bytes):
                continue
            if isinstance(value, (int, float, str, bool)):
                result[tag_name] = value
            elif isinstance(value, tuple):
                result[tag_name] = [float(v) if hasattr(v, '__float__') else str(v) for v in value]
            else:
                result[tag_name] = str(value)
        except Exception:
            continue
    return result


def resize_photo(image_file, max_edge=1920, quality=85):
    """Resize a photo, normalize orientation, and convert to JPEG.

    Returns an InMemoryUploadedFile with .jpg extension.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    return InMemoryUploadedFile(
        file=buffer,
        field_name="photo",
        name="photo.jpg",
        content_type="image/jpeg",
        size=buffer.getbuffer().nbytes,
        charset=None,
    )
