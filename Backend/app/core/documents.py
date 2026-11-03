import os
import json
from io import BytesIO
import hashlib
from PIL import Image, ImageOps, ImageFilter
import cv2
import numpy as np
import imagehash
import pytesseract
import pymupdf
from app.config import settings
from app.models import new_id

BLUR_THRESHOLD = 100.0
RESIZE_MAX_SIDE = 1600


def detect_kind(data):
    """Detect file type from the first bytes."""
    if len(data) < 8:
        raise ValueError("Only JPG, PNG and PDF files are allowed.")
    
    if data[:3] == b'\xff\xd8\xff':
        return "jpeg"
    
    if data[:8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
        return "png"
    
    if data[:5] == b'%PDF-':
        return "pdf"
    
    raise ValueError("Only JPG, PNG and PDF files are allowed.")


def check_file(data):
    """Check file size and type."""
    if len(data) == 0:
        raise ValueError("The file is empty.")
    
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"File is larger than {settings.max_upload_mb} MB.")
    
    return detect_kind(data)


def file_sha256(data):
    """Compute SHA256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def dms_to_decimal(dms, ref):
    """Convert GPS degrees/minutes/seconds to decimal."""
    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal


def read_exif(image):
    """Read EXIF metadata from an image."""
    try:
        exif_data = image.getexif()
        if not exif_data:
            return {"taken_at": None, "camera": None, "gps": None}
        
        taken_at = None
        datetime_original = exif_data.get(0x9003)
        if not datetime_original:
            exif_ifd = exif_data.get_ifd(0x8769)
            datetime_original = exif_ifd.get(0x9003) if exif_ifd else None
        
        if not datetime_original:
            datetime_original = exif_data.get(0x0132)
        
        if datetime_original:
            try:
                from datetime import datetime
                dt = datetime.strptime(datetime_original, "%Y:%m:%d %H:%M:%S")
                taken_at = dt.isoformat()
            except:
                taken_at = None
        
        camera = None
        make = exif_data.get(0x010f)
        model = exif_data.get(0x0110)
        if make or model:
            parts = []
            if make:
                parts.append(make.strip())
            if model:
                parts.append(model.strip())
            camera = " ".join(parts)
        
        gps = None
        gps_ifd = exif_data.get_ifd(0x8825)
        if gps_ifd:
            lat_ref = gps_ifd.get(1)
            lat_dms = gps_ifd.get(2)
            lon_ref = gps_ifd.get(3)
            lon_dms = gps_ifd.get(4)
            
            if lat_ref and lat_dms and lon_ref and lon_dms:
                lat = dms_to_decimal(lat_dms, lat_ref)
                lon = dms_to_decimal(lon_dms, lon_ref)
                gps = {"lat": lat, "lon": lon}
        
        return {"taken_at": taken_at, "camera": camera, "gps": gps}
    except:
        return {"taken_at": None, "camera": None, "gps": None}


def image_phash(image):
    """Compute perceptual hash."""
    return str(imagehash.phash(image))


def blur_score(image):
    """Compute blur score using Laplacian variance."""
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def make_resized(image):
    """Resize image to fit within max dimensions."""
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    result = image.copy()
    result.thumbnail((RESIZE_MAX_SIDE, RESIZE_MAX_SIDE))
    return result


def cleanup_for_ocr(image):
    """Prepare image for OCR."""
    image = ImageOps.exif_transpose(image)
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray)
    
    gray_np = np.array(gray)
    denoised = cv2.fastNlMeansDenoising(gray_np, None, 10, 7, 21)
    
    threshold_value, thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return Image.fromarray(thresholded)


def run_ocr(path):
    """Run OCR on an image or PDF."""
    full_path = os.path.join(settings.storage_dir, path)
    
    kind = detect_kind(open(full_path, "rb").read())
    
    if kind == "pdf":
        doc = pymupdf.open(full_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img_data = pix.tobytes("png")
        image = Image.open(BytesIO(img_data))
    else:
        image = Image.open(full_path)
    
    cleaned = cleanup_for_ocr(image)
    
    try:
        text = pytesseract.image_to_string(cleaned)
        return text
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError("Tesseract is not installed or not on PATH.")


def save_upload(claim_id, data):
    """Save uploaded file and create thumbnail."""
    kind = check_file(data)
    
    file_id = new_id()
    
    ext_map = {"jpeg": "jpg", "png": "png", "pdf": "pdf"}
    ext = ext_map[kind]
    
    original_path = f"originals/{claim_id}/{file_id}.{ext}"
    resized_path = f"resized/{claim_id}/{file_id}.jpg"
    
    original_full = os.path.join(settings.storage_dir, original_path)
    resized_full = os.path.join(settings.storage_dir, resized_path)
    
    os.makedirs(os.path.dirname(original_full), exist_ok=True)
    os.makedirs(os.path.dirname(resized_full), exist_ok=True)
    
    with open(original_full, "wb") as f:
        f.write(data)
    
    mime_map = {"jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}
    mime_type = mime_map[kind]
    
    size_bytes = len(data)
    hash_value = file_sha256(data)
    
    if kind in ["jpeg", "png"]:
        try:
            image = Image.open(BytesIO(data))
            image.load()
        except:
            raise ValueError("The image could not be read.")
        
        exif = read_exif(image)
        img_hash = image_phash(image)
        quality = blur_score(image)
        
        resized = make_resized(image)
        resized.save(resized_full, "JPEG", quality=85)
    else:
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except:
            raise ValueError("The PDF could not be read.")
        
        page = doc[0]
        pix = page.get_pixmap(dpi=100)
        pix.save(resized_full)
        
        img_hash = ""
        quality = None
        exif = {}
    
    return {
        "original_path": original_path.replace("\\", "/"),
        "resized_path": resized_path.replace("\\", "/"),
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "file_hash": hash_value,
        "image_hash": img_hash,
        "quality_score": quality,
        "exif": exif,
    }
