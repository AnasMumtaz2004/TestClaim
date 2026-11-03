import pytest
import shutil
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter
import pymupdf
from app.core.documents import (
    detect_kind,
    check_file,
    file_sha256,
    read_exif,
    image_phash,
    blur_score,
    save_upload,
    run_ocr,
    BLUR_THRESHOLD,
)
from app.config import settings


def make_png_bytes():
    """Create a small PNG image."""
    img = Image.new("RGB", (100, 100), color="white")
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_jpeg_bytes():
    """Create a small JPEG image."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def make_pdf_bytes():
    """Create a one-page PDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 50), "Test")
    buf = BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_text_file_rejected():
    """A text file is rejected."""
    with pytest.raises(ValueError, match="Only JPG, PNG and PDF"):
        detect_kind(b"hello world")


def test_renamed_text_rejected():
    """A text file renamed .jpg is rejected."""
    with pytest.raises(ValueError, match="Only JPG, PNG and PDF"):
        detect_kind(b"not an image")


def test_empty_rejected():
    """Empty bytes are rejected."""
    with pytest.raises(ValueError, match="empty"):
        check_file(b"")


def test_oversized_rejected(monkeypatch):
    """A file bigger than the limit is rejected."""
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    png_header = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
    data = png_header + b"x" * (2 * 1024 * 1024)
    with pytest.raises(ValueError, match="larger than"):
        check_file(data)


def test_valid_files_accepted():
    """PNG, JPEG and PDF are accepted."""
    png = make_png_bytes()
    jpeg = make_jpeg_bytes()
    pdf = make_pdf_bytes()
    
    assert detect_kind(png) == "png"
    assert detect_kind(jpeg) == "jpeg"
    assert detect_kind(pdf) == "pdf"


def test_sha256_deterministic():
    """Same bytes give same hash, different bytes give different hashes."""
    data1 = b"hello"
    data2 = b"hello"
    data3 = b"world"
    
    assert file_sha256(data1) == file_sha256(data2)
    assert file_sha256(data1) != file_sha256(data3)


def test_phash_duplicate_detection():
    """Similar images have low hamming distance, different images have high distance."""
    img1 = Image.new("RGB", (200, 200), color="white")
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([10, 10, 50, 50], fill="black")
    
    buf1 = BytesIO()
    img1.save(buf1, "JPEG", quality=95)
    buf1.seek(0)
    img1_reload = Image.open(buf1)
    
    buf2 = BytesIO()
    img1.save(buf2, "JPEG", quality=60)
    buf2.seek(0)
    img2 = Image.open(buf2)
    
    hash1 = image_phash(img1_reload)
    hash2 = image_phash(img2)
    
    distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    assert distance <= 5
    
    img3 = Image.new("RGB", (200, 200), color="white")
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([150, 150, 190, 190], fill="black")
    
    hash3 = image_phash(img3)
    distance2 = sum(c1 != c2 for c1, c2 in zip(hash1, hash3))
    assert distance2 > 10


def test_blur_detection():
    """Sharp image scores above threshold, blurred below."""
    img = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(img)
    for i in range(0, 200, 10):
        color = "black" if (i // 10) % 2 == 0 else "white"
        draw.rectangle([i, 0, i + 10, 200], fill=color)
    
    sharp_score = blur_score(img)
    assert sharp_score > BLUR_THRESHOLD
    
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6))
    blur_score_val = blur_score(blurred)
    assert blur_score_val < BLUR_THRESHOLD


def test_read_exif_no_data():
    """Image with no EXIF returns all None."""
    img = Image.new("RGB", (100, 100), color="red")
    exif = read_exif(img)
    assert exif["taken_at"] is None
    assert exif["camera"] is None
    assert exif["gps"] is None


def test_read_exif_with_datetime():
    """Image with DateTime EXIF returns taken_at."""
    from PIL.ExifTags import TAGS
    
    img = Image.new("RGB", (100, 100), color="green")
    exif_dict = img.getexif()
    exif_dict[0x0132] = "2026:01:15 10:30:00"
    
    img_with_exif = Image.new("RGB", (100, 100), color="green")
    img_with_exif.info["exif"] = exif_dict.tobytes()
    
    buf = BytesIO()
    img.save(buf, "JPEG", exif=exif_dict)
    buf.seek(0)
    img_reload = Image.open(buf)
    
    exif = read_exif(img_reload)
    assert exif["taken_at"] == "2026-01-15T10:30:00"


def test_save_upload(monkeypatch, tmp_path):
    """Save upload creates original and resized files."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    
    png_data = make_png_bytes()
    result = save_upload("test-claim-id", png_data)
    
    assert "originals/test-claim-id/" in result["original_path"]
    assert "resized/test-claim-id/" in result["resized_path"]
    assert result["mime_type"] == "image/png"
    assert result["size_bytes"] == len(png_data)
    assert len(result["file_hash"]) == 64
    assert len(result["image_hash"]) > 0
    
    original_full = tmp_path / result["original_path"]
    resized_full = tmp_path / result["resized_path"]
    assert original_full.exists()
    assert resized_full.exists()
    
    pdf_data = make_pdf_bytes()
    result_pdf = save_upload("test-claim-id", pdf_data)
    assert result_pdf["quality_score"] is None


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract not installed")
def test_run_ocr(monkeypatch, tmp_path):
    """OCR returns a string."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    
    img = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(img)
    
    buf = BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()
    
    result = save_upload("ocr-test", data)
    text = run_ocr(result["original_path"])
    assert isinstance(text, str)
