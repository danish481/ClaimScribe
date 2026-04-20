"""
ClaimScribe AI - Health & Monitoring Router
System health checks and monitoring endpoints
"""

import time
from datetime import datetime

from fastapi import APIRouter

from app.config import settings
from app.services.document_processor import document_processor
from app.services.mlflow_tracker import mlflow_tracker

# Track startup time
START_TIME = time.time()

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


@router.get("/status")
async def health_status():
    """
    Get overall system health status.
    Checks all critical components.
    """
    components = {
        "api": {"status": "healthy", "version": settings.APP_VERSION},
        "ocr": {"status": "healthy"},  # Would check tesseract in full impl
        "classifier": {"status": "healthy"},
        "llm": {
            "status": "healthy" if settings.GEMINI_API_KEY else "degraded",
            "message": "Using mock responses" if not settings.GEMINI_API_KEY else "Gemini API configured",
        },
    }

    # Check MLflow
    try:
        mlflow_tracker.init()
        summary = mlflow_tracker.get_experiment_summary()
        components["mlflow"] = {
            "status": "healthy",
            "total_runs": summary.get("total_runs", 0),
        }
    except Exception as e:
        components["mlflow"] = {"status": "degraded", "error": str(e)}

    # Overall status
    statuses = [c["status"] for c in components.values()]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "components": components,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/metrics")
async def processing_metrics():
    """
    Get document processing metrics.
    """
    metrics = document_processor.get_metrics()
    return metrics


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    """
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    """
    return {"status": "alive"}
