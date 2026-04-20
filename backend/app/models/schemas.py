"""
ClaimScribe AI - Pydantic Schemas
Request/Response models for API endpoints
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────

class DocumentType(str, Enum):
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    PHARMACY = "pharmacy"
    UNKNOWN = "unknown"

class FileFormat(str, Enum):
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    TIFF = "tiff"
    TIF = "tif"
    DOCX = "docx"
    TXT = "txt"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


# ── Document Schemas ──────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    document_id: str
    filename: str
    status: ProcessingStatus
    message: str
    detected_type: Optional[DocumentType] = None
    confidence: Optional[float] = None
    extracted_text_preview: Optional[str] = None
    processing_time_ms: Optional[float] = None
    phi_detected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentDetail(BaseModel):
    """Full document details."""
    document_id: str
    filename: str
    file_format: FileFormat
    file_size_bytes: int
    status: ProcessingStatus
    detected_type: DocumentType
    confidence: float
    extracted_text: str
    masked_text: Optional[str] = None  # PHI-masked version
    structured_data: Optional[Dict[str, Any]] = None
    phi_detected: bool = False
    phi_summary: Optional[Dict[str, List[str]]] = None
    mlflow_run_id: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

class DocumentListResponse(BaseModel):
    """List of documents with pagination."""
    total: int
    documents: List[DocumentDetail]
    page: int = 1
    page_size: int = 20


# ── DataFrame / Structured Data Schemas ───────────────────

class DataFrameExportRequest(BaseModel):
    """Request to export documents as DataFrame."""
    document_ids: Optional[List[str]] = None  # None = all
    format: ExportFormat = ExportFormat.CSV
    include_inferred: bool = True
    mask_phi: bool = True

class DataFrameExportResponse(BaseModel):
    """Response with exported data."""
    export_id: str
    format: ExportFormat
    file_path: str
    row_count: int
    column_names: List[str]
    inferred_columns: List[str]
    download_url: str
    expires_at: datetime


# ── LLM Schemas ───────────────────────────────────────────

class LLMQueryRequest(BaseModel):
    """Request to query the healthcare LLM."""
    query: str = Field(..., min_length=1, max_length=4000)
    document_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    temperature: Optional[float] = None
    include_sources: bool = True

class LLMQueryResponse(BaseModel):
    """Response from healthcare LLM."""
    response: str
    conversation_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    processing_time_ms: float
    tokens_used: Optional[int] = None
    model: str

class ConversationSummary(BaseModel):
    """Summary of a conversation."""
    conversation_id: str
    message_count: int
    last_message_at: datetime
    preview: str


# ── Health / Monitoring Schemas ───────────────────────────

class HealthStatus(BaseModel):
    """System health status."""
    status: str  # healthy | degraded | unhealthy
    version: str
    environment: str
    uptime_seconds: float
    components: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProcessingMetrics(BaseModel):
    """Document processing metrics."""
    total_documents: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    avg_processing_time_ms: float
    avg_confidence: float
    phi_detection_rate: float
    error_rate: float
    time_range: str


# ── Classifier Training Schemas ───────────────────────────

class ClassifierMetrics(BaseModel):
    """Classifier performance metrics."""
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    confusion_matrix: List[List[int]]
    training_samples: int
    test_samples: int
    mlflow_run_id: str
