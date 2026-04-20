"""
ClaimScribe AI - Document Processor Service
Orchestrates document ingestion, OCR, classification, and data structuring
"""

import io
import uuid
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
from fastapi import UploadFile

from app.config import settings, UPLOAD_DIR, EXPORT_DIR
from app.models.schemas import (
    DocumentType, ProcessingStatus, DocumentUploadResponse, DocumentDetail,
    ExportFormat, DataFrameExportResponse
)
from app.services.ocr_service import ocr_service, OCRProcessingError, UnsupportedFormatError
from app.services.classifier import classifier
from app.services.llm_service import llm_service
from app.core.security import encryption, PHIDetector, AuditLogger


# ── In-Memory Document Store (Replace with DB in production) ──

class DocumentStore:
    """Simple document store for demo. Use PostgreSQL in production."""

    def __init__(self):
        self._documents: Dict[str, DocumentDetail] = {}

    def save(self, doc: DocumentDetail):
        self._documents[doc.document_id] = doc

    def get(self, doc_id: str) -> Optional[DocumentDetail]:
        return self._documents.get(doc_id)

    def list_all(self) -> List[DocumentDetail]:
        return sorted(self._documents.values(), key=lambda d: d.created_at, reverse=True)

    def delete(self, doc_id: str):
        self._documents.pop(doc_id, None)

    def to_dataframe(self, document_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """Convert documents to pandas DataFrame with inferred columns."""
        docs = [
            self._documents[did] for did in document_ids
            if did in self._documents
        ] if document_ids else list(self._documents.values())

        if not docs:
            return pd.DataFrame()

        rows = []
        for doc in docs:
            row = {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "file_format": doc.file_format.value if hasattr(doc.file_format, 'value') else doc.file_format,
                "file_size_bytes": doc.file_size_bytes,
                "detected_type": doc.detected_type.value if hasattr(doc.detected_type, 'value') else doc.detected_type,
                "confidence": doc.confidence,
                "status": doc.status.value if hasattr(doc.status, 'value') else doc.status,
                "phi_detected": doc.phi_detected,
                "extracted_text_length": len(doc.extracted_text),
                "mlflow_run_id": doc.mlflow_run_id or "",
                "created_at": doc.created_at,
                "processed_at": doc.processed_at,
            }

            # Add inferred columns from structured data
            if doc.structured_data:
                for key, value in doc.structured_data.items():
                    col_name = f"inferred_{key}"
                    if isinstance(value, (str, int, float, bool)):
                        row[col_name] = value

            rows.append(row)

        df = pd.DataFrame(rows)

        # Add inferred category confidence columns
        if docs:
            for doc_type in DocumentType:
                if doc_type == DocumentType.UNKNOWN:
                    continue
                col_name = f"confidence_{doc_type.value}"
                df[col_name] = df["document_id"].apply(
                    lambda did: self._documents.get(did, DocumentDetail(
                        document_id="", filename="", file_format="", file_size_bytes=0,
                        status=ProcessingStatus.COMPLETED, detected_type=DocumentType.UNKNOWN,
                        confidence=0, extracted_text="", created_at=datetime.utcnow()
                    )).structured_data.get(f"score_{doc_type.value}", 0.0)
                    if self._documents.get(did) and self._documents[did].structured_data else 0.0
                )

        return df

    def get_count(self) -> int:
        return len(self._documents)


document_store = DocumentStore()


class DocumentProcessor:
    """
    Main document processing orchestrator.

    Pipeline:
    1. Receive uploaded file
    2. Validate format and size
    3. Encrypt and store
    4. Extract text (OCR if needed)
    5. Detect PHI
    6. Classify document
    7. Structure data
    8. Log to MLflow
    9. Return result
    """

    SUPPORTED_FORMATS = {
        'pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'docx', 'txt'
    }

    def __init__(self):
        self.store = document_store
        self._exports: Dict[str, Path] = {}
        self._export_expiry: Dict[str, datetime] = {}

    async def process_upload(self, file: UploadFile) -> DocumentUploadResponse:
        """
        Process an uploaded document through the full pipeline.

        Args:
            file: FastAPI UploadFile

        Returns:
            DocumentUploadResponse with classification results
        """
        start_time = time.time()
        doc_id = str(uuid.uuid4())

        try:
            # ── 1. Validate ─────────────────────────────────
            original_filename = file.filename or "unknown"
            file_ext = self._get_extension(original_filename)

            if file_ext not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported file format: {file_ext}")

            # Read file content
            content = await file.read()
            file_size = len(content)

            if file_size > settings.MAX_FILE_SIZE:
                raise ValueError(f"File too large: {file_size} bytes (max: {settings.MAX_FILE_SIZE})")

            # ── 2. Encrypt and Store ────────────────────────
            encrypted_content = encryption.encrypt(content)
            storage_path = UPLOAD_DIR / f"{doc_id}.enc"
            storage_path.write_bytes(encrypted_content)

            AuditLogger.log_event(
                event_type="document_uploaded",
                resource_type="document",
                resource_id=doc_id,
                details={"filename": original_filename, "size": file_size, "format": file_ext}
            )

            # ── 3. Extract Text ─────────────────────────────
            try:
                extracted_text = ocr_service.extract_text(content, file_ext)
            except Exception as e:
                return DocumentUploadResponse(
                    document_id=doc_id,
                    filename=original_filename,
                    status=ProcessingStatus.FAILED,
                    message=f"Text extraction failed: {str(e)}"
                )

            if not extracted_text or len(extracted_text.strip()) < 10:
                return DocumentUploadResponse(
                    document_id=doc_id,
                    filename=original_filename,
                    status=ProcessingStatus.FAILED,
                    message="Could not extract sufficient text from document. Please ensure the file is readable."
                )

            # ── 4. PHI Detection ────────────────────────────
            phi_detected = PHIDetector.has_phi(extracted_text)
            phi_summary = PHIDetector.detect_phi(extracted_text) if phi_detected else None
            masked_text = PHIDetector.mask_phi(extracted_text) if phi_detected else None

            # ── 5. Classify ─────────────────────────────────
            classification = classifier.classify(extracted_text, document_id=doc_id)

            # ── 6. Structure Data ───────────────────────────
            structured_data = self._structure_data(
                extracted_text,
                classification,
                phi_summary
            )

            # ── 7. Save Document Record ─────────────────────
            processing_time = (time.time() - start_time) * 1000

            doc_detail = DocumentDetail(
                document_id=doc_id,
                filename=original_filename,
                file_format=file_ext,
                file_size_bytes=file_size,
                status=ProcessingStatus.COMPLETED,
                detected_type=classification["predicted_type"],
                confidence=classification["confidence"],
                extracted_text=extracted_text,
                masked_text=masked_text,
                structured_data=structured_data,
                phi_detected=phi_detected,
                phi_summary=phi_summary,
                mlflow_run_id=classification.get("mlflow_run_id"),
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
            )

            self.store.save(doc_detail)

            # ── 8. Return Response ──────────────────────────
            preview = extracted_text[:300].replace('\n', ' ')
            if len(extracted_text) > 300:
                preview += "..."

            return DocumentUploadResponse(
                document_id=doc_id,
                filename=original_filename,
                status=ProcessingStatus.COMPLETED,
                message=f"Document processed successfully. Classified as {classification['predicted_type'].value} claim.",
                detected_type=classification["predicted_type"],
                confidence=classification["confidence"],
                extracted_text_preview=preview,
                processing_time_ms=round(processing_time, 2),
                phi_detected=phi_detected,
            )

        except ValueError as e:
            return DocumentUploadResponse(
                document_id=doc_id,
                filename=file.filename or "unknown",
                status=ProcessingStatus.FAILED,
                message=str(e)
            )
        except Exception as e:
            AuditLogger.log_event(
                event_type="document_processing_error",
                resource_type="document",
                resource_id=doc_id,
                details={"error": str(e), "filename": file.filename}
            )
            return DocumentUploadResponse(
                document_id=doc_id,
                filename=file.filename or "unknown",
                status=ProcessingStatus.FAILED,
                message=f"Unexpected error: {str(e)}"
            )

    async def process_camera_capture(self, image_bytes: bytes, filename: str = "capture.jpg") -> DocumentUploadResponse:
        """Process a camera-captured image."""
        from fastapi import UploadFile
        from starlette.datastructures import UploadFile as StarletteUploadFile

        # Wrap bytes in UploadFile
        upload_file = StarletteUploadFile(
            filename=filename,
            file=io.BytesIO(image_bytes),
        )
        return await self.process_upload(upload_file)

    def _structure_data(
        self,
        text: str,
        classification: Dict,
        phi_summary: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Extract structured data from document text.
        Creates inferred columns for DataFrame export.
        """
        structured = {
            "classification_method": classification["method"],
            "is_ambiguous": classification["is_ambiguous"],
        }

        # Add classification scores
        for doc_type, score in classification.get("scores", {}).items():
            structured[f"score_{doc_type}"] = score

        # Extract potential dates
        import re
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
        ]
        dates_found = []
        for pattern in date_patterns:
            dates_found.extend(re.findall(pattern, text))
        structured["dates_found"] = dates_found[:10]  # Limit to 10
        structured["date_count"] = len(dates_found)

        # Extract potential monetary amounts
        money_pattern = r'\$[\d,]+\.?\d*'
        amounts = re.findall(money_pattern, text)
        structured["monetary_amounts"] = amounts[:20]
        structured["amount_count"] = len(amounts)

        # Extract potential codes (ICD, CPT, etc.)
        icd_pattern = r'\b[A-Z]\d{2}(?:\.\d{1,2})?\b'
        cpt_pattern = r'\b\d{5}\b'
        structured["potential_icd_codes"] = re.findall(icd_pattern, text)[:20]
        structured["potential_cpt_codes"] = re.findall(cpt_pattern, text)[:20]

        # Word count and language indicators
        words = text.split()
        structured["word_count"] = len(words)
        structured["character_count"] = len(text)

        # PHI summary
        if phi_summary:
            structured["phi_types_detected"] = list(phi_summary.keys())
            structured["phi_instance_count"] = sum(len(v) for v in phi_summary.values())

        return structured

    def get_document(self, doc_id: str) -> Optional[DocumentDetail]:
        """Get document details by ID."""
        return self.store.get(doc_id)

    def list_documents(self) -> List[DocumentDetail]:
        """List all processed documents."""
        return self.store.list_all()

    def export_dataframe(
        self,
        document_ids: Optional[List[str]] = None,
        format: ExportFormat = ExportFormat.CSV,
        mask_phi: bool = True,
    ) -> DataFrameExportResponse:
        """
        Export documents as a structured DataFrame.

        Returns:
            DataFrameExportResponse with download URL
        """
        df = self.store.to_dataframe(document_ids)

        if df.empty:
            raise ValueError("No documents to export")

        # Mask PHI in text columns if requested
        if mask_phi:
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].apply(
                        lambda x: PHIDetector.mask_phi(str(x)) if isinstance(x, str) and PHIDetector.has_phi(str(x)) else x
                    )

        # Generate export file
        export_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format == ExportFormat.CSV:
            file_path = EXPORT_DIR / f"export_{timestamp}_{export_id}.csv"
            df.to_csv(file_path, index=False)
        elif format == ExportFormat.EXCEL:
            file_path = EXPORT_DIR / f"export_{timestamp}_{export_id}.xlsx"
            df.to_excel(file_path, index=False, engine='openpyxl')
        else:  # JSON
            file_path = EXPORT_DIR / f"export_{timestamp}_{export_id}.json"
            df.to_json(file_path, orient='records', indent=2)

        # Identify inferred columns
        inferred_cols = [c for c in df.columns if c.startswith("inferred_") or c.startswith("confidence_")]

        # Register export for download
        expires_at = datetime.utcnow() + timedelta(hours=settings.EXPORT_LINK_TTL_HOURS)
        self._exports[export_id] = file_path
        self._export_expiry[export_id] = expires_at

        return DataFrameExportResponse(
            export_id=export_id,
            format=format,
            file_path=str(file_path),
            row_count=len(df),
            column_names=list(df.columns),
            inferred_columns=inferred_cols,
            download_url=f"/api/v1/documents/export/{export_id}/download",
            expires_at=expires_at,
        )

    def get_export_path(self, export_id: str) -> Optional[Path]:
        """Return export file path if it exists and has not expired."""
        path = self._exports.get(export_id)
        expiry = self._export_expiry.get(export_id)
        if path is None or expiry is None:
            return None
        if datetime.utcnow() > expiry:
            return None
        if not path.exists():
            return None
        return path

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Get lowercase file extension."""
        return filename.split('.')[-1].lower() if '.' in filename else ''

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics for monitoring."""
        docs = self.store.list_all()
        total = len(docs)

        if total == 0:
            return {
                "total_documents": 0,
                "by_type": {},
                "by_status": {"completed": 0, "failed": 0},
                "avg_processing_time_ms": 0,
                "avg_confidence": 0,
                "phi_detection_rate": 0,
                "error_rate": 0,
            }

        by_type = {}
        by_status = {}
        confidences = []
        phi_count = 0
        failed = 0

        for doc in docs:
            # By type
            type_val = doc.detected_type.value if hasattr(doc.detected_type, 'value') else str(doc.detected_type)
            by_type[type_val] = by_type.get(type_val, 0) + 1

            # By status
            status_val = doc.status.value if hasattr(doc.status, 'value') else str(doc.status)
            by_status[status_val] = by_status.get(status_val, 0) + 1

            confidences.append(doc.confidence)
            if doc.phi_detected:
                phi_count += 1
            if status_val == "failed":
                failed += 1

        return {
            "total_documents": total,
            "by_type": by_type,
            "by_status": by_status,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "phi_detection_rate": phi_count / total,
            "error_rate": failed / total,
            "time_range": "all_time",
        }


# ── Singleton ─────────────────────────────────────────────
document_processor = DocumentProcessor()
