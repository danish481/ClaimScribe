"""
ClaimScribe AI - Documents Router
API endpoints for document upload, processing, and management
"""

from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse

from app.models.schemas import (
    DocumentUploadResponse, DocumentDetail, DocumentListResponse,
    ExportFormat, DataFrameExportResponse, ProcessingStatus
)
from app.services.document_processor import document_processor
from app.services.classifier import classifier
from app.core.security import AuditLogger

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document file to process (PDF, PNG, JPG, TIFF, DOCX, TXT)"),
):
    """
    Upload and process a health insurance claims document.

    Supports: PDF, PNG, JPG, JPEG, TIFF, TIF, DOCX, TXT
    Files are encrypted at rest and processed through OCR + classification pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    result = await document_processor.process_upload(file)

    if result.status == ProcessingStatus.FAILED:
        raise HTTPException(status_code=422, detail=result.message)

    return result


@router.post("/capture", response_model=DocumentUploadResponse)
async def capture_document(
    image: UploadFile = File(..., description="Camera-captured image"),
):
    """
    Process a camera-captured image (e.g., from mobile device).

    Optimized for photos of physical documents with automatic preprocessing.
    """
    if not image.filename:
        raise HTTPException(status_code=400, detail="No image provided")

    result = await document_processor.process_upload(image)

    if result.status == ProcessingStatus.FAILED:
        raise HTTPException(status_code=422, detail=result.message)

    return result


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    doc_type: Optional[str] = Query(None, description="Filter by type: inpatient, outpatient, pharmacy"),
):
    """
    List all processed documents with pagination and optional type filtering.
    """
    all_docs = document_processor.list_documents()

    if doc_type:
        all_docs = [d for d in all_docs if d.detected_type.value == doc_type]

    total = len(all_docs)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_docs[start:end]

    return DocumentListResponse(
        total=total,
        documents=paginated,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str):
    """
    Get detailed information about a processed document.
    """
    doc = document_processor.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    AuditLogger.log_event(
        event_type="document_viewed",
        resource_type="document",
        resource_id=document_id,
    )

    return doc


@router.post("/export", response_model=DataFrameExportResponse)
async def export_documents(
    document_ids: Optional[List[str]] = Form(None),
    format: ExportFormat = Form(ExportFormat.CSV),
    mask_phi: bool = Form(True),
):
    """
    Export processed documents as a structured DataFrame.

    Returns a downloadable file with all document data including inferred columns
    from the classification process.
    """
    try:
        result = document_processor.export_dataframe(
            document_ids=document_ids,
            format=format,
            mask_phi=mask_phi,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/{export_id}/download")
async def download_export(export_id: str):
    """
    Download an exported DataFrame file.
    """
    path = document_processor.get_export_path(export_id)
    if not path:
        raise HTTPException(status_code=404, detail="Export not found or has expired")

    mime_map = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
    }
    media_type = mime_map.get(path.suffix.lower(), "application/octet-stream")

    AuditLogger.log_event(event_type="export_downloaded", resource_id=export_id)
    return FileResponse(path, filename=path.name, media_type=media_type)


@router.get("/metrics/classifier")
async def get_classifier_metrics():
    """
    Get current classifier performance metrics from MLflow.
    """
    from app.services.mlflow_tracker import mlflow_tracker
    return mlflow_tracker.get_experiment_summary()
