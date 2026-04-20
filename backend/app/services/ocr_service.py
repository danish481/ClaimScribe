"""
ClaimScribe AI - OCR Service
Handles text extraction from images, scanned PDFs, and various document formats
"""

import io
import tempfile
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
from pdf2image import convert_from_path

from app.config import settings
from app.core.security import AuditLogger

# Configure tesseract path
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCRService:
    """Advanced OCR service for healthcare document processing."""

    def __init__(self):
        self.dpi = settings.OCR_DPI

    def extract_from_image(self, image_bytes: bytes, preprocess: bool = True) -> str:
        """Extract text from image bytes (PNG, JPEG, TIFF)."""
        try:
            image = Image.open(io.BytesIO(image_bytes))

            if preprocess:
                image = self._preprocess_image(image)

            # OCR with optimal config for medical documents
            custom_config = r'--oem 3 --psm 6 -l eng'
            text = pytesseract.image_to_string(image, config=custom_config)

            AuditLogger.log_event(
                event_type="ocr_extract_image",
                resource_type="image",
                details={"preprocessed": preprocess, "text_length": len(text)}
            )

            return text.strip()

        except Exception as e:
            AuditLogger.log_event(
                event_type="ocr_extract_image_failed",
                resource_type="image",
                details={"error": str(e)}
            )
            raise OCRProcessingError(f"OCR failed: {str(e)}")

    def extract_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF.
        First tries direct text extraction, falls back to OCR for scanned PDFs.
        """
        text_parts = []

        # Try direct text extraction first
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
        except Exception:
            pass

        direct_text = "\n".join(text_parts).strip()

        # If direct extraction yielded little text, likely a scanned PDF - use OCR
        if len(direct_text) < 100:
            try:
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name

                images = convert_from_path(tmp_path, dpi=self.dpi)
                ocr_texts = []

                for img in images:
                    img = self._preprocess_image(img)
                    custom_config = r'--oem 3 --psm 6 -l eng'
                    page_text = pytesseract.image_to_string(img, config=custom_config)
                    ocr_texts.append(page_text)

                Path(tmp_path).unlink(missing_ok=True)
                ocr_result = "\n".join(ocr_texts).strip()

                if len(ocr_result) > len(direct_text):
                    return ocr_result

            except Exception as e:
                if direct_text:
                    return direct_text
                raise OCRProcessingError(f"PDF OCR failed: {str(e)}")

        return direct_text

    def extract_from_docx(self, docx_bytes: bytes) -> str:
        """Extract text from DOCX files."""
        try:
            from docx import Document
            doc = Document(io.BytesIO(docx_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except Exception as e:
            raise OCRProcessingError(f"DOCX extraction failed: {str(e)}")

    def extract_text(self, file_bytes: bytes, file_extension: str) -> str:
        """Route to appropriate extractor based on file type."""
        ext = file_extension.lower().lstrip('.')

        extractors = {
            'pdf': self.extract_from_pdf,
            'png': self.extract_from_image,
            'jpg': self.extract_from_image,
            'jpeg': self.extract_from_image,
            'tif': self.extract_from_image,
            'tiff': self.extract_from_image,
            'docx': self.extract_from_docx,
            'txt': lambda b: b.decode('utf-8', errors='ignore'),
        }

        extractor = extractors.get(ext)
        if not extractor:
            raise UnsupportedFormatError(f"Unsupported file format: {ext}")

        return extractor(file_bytes)

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply image preprocessing for better OCR accuracy."""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        # Denoise
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Resize if too small (minimum 150 DPI equivalent)
        min_width = 1200
        if image.width < min_width:
            ratio = min_width / image.width
            new_size = (min_width, int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)

        return image


# ── Custom Exceptions ─────────────────────────────────────

class OCRProcessingError(Exception):
    """Raised when OCR processing fails."""
    pass

class UnsupportedFormatError(Exception):
    """Raised when file format is not supported."""
    pass


# ── Singleton ─────────────────────────────────────────────
ocr_service = OCRService()
