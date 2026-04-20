"""
ClaimScribe AI - Main Application
FastAPI entry point with CORS, middleware, and route registration
"""

import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import documents, llm, health

# ── Application Factory ───────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        description="""
        **ClaimScribe AI** - Healthcare Document Intelligence Platform

        Automated document ingestion and classification for health insurance claims processing.
        HIPAA-aware, MLflow-tracked, and production-ready.

        ## Features
        - **Document Upload**: PDF, PNG, JPG, TIFF, DOCX, TXT
        - **OCR**: Automatic text extraction from scanned documents
        - **Classification**: AI-powered claim type detection (inpatient/outpatient/pharmacy)
        - **Healthcare LLM**: Domain-specific AI assistant for document analysis
        - **Data Export**: Structured DataFrame export with inferred columns
        - **MLflow Tracking**: Full experiment and model versioning
        - **HIPAA Compliance**: Encryption, PHI detection, audit logging

        ## Security
        All endpoints implement:
        - Request logging and audit trails
        - PHI detection and masking
        - Encryption at rest for uploaded documents
        - CORS protection
        """,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "ClaimScribe AI Team",
            "email": "support@claimscribe.ai",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://claimscribe.ai/license",
        },
    )

    # ── Middleware ────────────────────────────────────────

    # CORS
    origins = settings.CORS_ORIGINS.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Hosts
    _allowed_hosts = settings.ALLOWED_HOSTS.split(",") if settings.ALLOWED_HOSTS != "*" else ["*"]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_allowed_hosts,
    )

    # Request Timing & Logging
    @app.middleware("http")
    async def add_request_metadata(request: Request, call_next):
        start_time = time.time()
        request.state.request_id = f"req_{int(start_time * 1000)}"

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))

        # Log request
        print(
            f"[{datetime.utcnow().isoformat()}] "
            f"{request.method} {request.url.path} "
            f"- {response.status_code} "
            f"- {process_time:.4f}s"
        )

        return response

    # ── Exception Handlers ────────────────────────────────

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "request_id": getattr(request.state, 'request_id', 'unknown'),
            },
        )

    # ── Routes ────────────────────────────────────────────

    # Include routers
    app.include_router(
        documents.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        llm.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        health.router,
        prefix=settings.API_V1_PREFIX,
    )

    # Monitoring alias: /api/v1/monitoring/metrics -> same handler as /api/v1/health/metrics
    from fastapi import APIRouter as _APIRouter
    from app.routers.health import processing_metrics
    _monitoring = _APIRouter(prefix=f"{settings.API_V1_PREFIX}/monitoring", tags=["Health & Monitoring"])
    _monitoring.add_api_route("/metrics", processing_metrics, methods=["GET"])
    app.include_router(_monitoring)

    # ── Root Endpoints ────────────────────────────────────

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs",
            "health_check": f"{settings.API_V1_PREFIX}/health/status",
        }

    @app.get("/health")
    async def simple_health():
        """Simple health check for load balancers."""
        return {"status": "healthy"}

    return app


# ── Create Application Instance ───────────────────────────
app = create_app()

# ── Startup/Shutdown Events ───────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print(f"\n{'='*60}")
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  API Prefix: {settings.API_V1_PREFIX}")
    print(f"{'='*60}\n")

    # Initialize MLflow
    try:
        from app.services.mlflow_tracker import mlflow_tracker
        mlflow_tracker.init()
        print("MLflow tracking initialized")
    except Exception as e:
        print(f"MLflow initialization warning: {e}")

    # Log startup event
    from app.core.security import AuditLogger
    AuditLogger.log_event(
        event_type="system_startup",
        details={"version": settings.APP_VERSION, "environment": settings.ENVIRONMENT},
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from app.core.security import AuditLogger
    AuditLogger.log_event(event_type="system_shutdown", details={})
    print(f"\n{settings.APP_NAME} shutting down gracefully.\n")
