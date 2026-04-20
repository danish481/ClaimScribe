import shutil
import pytest
from app.services.ocr_service import ocr_service

TXT_CONTENT = b"Hello world pharmacy prescription"


def test_extract_text_txt():
    result = ocr_service.extract_text(TXT_CONTENT, "txt")
    assert isinstance(result, str)
    assert "Hello world" in result
    assert "pharmacy" in result


def test_extract_text_txt_unicode():
    content = "Patient name: José García. Claim #001.".encode("utf-8")
    result = ocr_service.extract_text(content, "txt")
    assert "García" in result


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract missing")
def test_extract_image_requires_tesseract():
    from app.services.ocr_service import OCRProcessingError
    # Ensure the image extractor at least invokes tesseract when available
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 30), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = ocr_service.extract_text(buf.getvalue(), "png")
    assert isinstance(result, str)
