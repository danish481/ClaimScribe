"""
ClaimScribe AI - Pipeline Router
Endpoints to trigger, monitor, and inspect the batch ingestion pipeline.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from app.services.pipeline_service import pipeline_service


class AssignRequest(BaseModel):
    target_category: str   # inpatient | outpatient | pharmacy
    assigned_by: str = "reviewer"

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ── Trigger ───────────────────────────────────────────────

@router.post("/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Manually trigger a pipeline run.
    Returns immediately; processing happens in background.
    Poll /status to see progress.
    """
    pending = pipeline_service.scan_inbox()
    background_tasks.add_task(_run_in_thread, "manual")
    return {
        "message": "Pipeline run started",
        "triggered_by": "manual",
        "inbox_files_queued": len(pending),
    }


async def _run_in_thread(triggered_by: str):
    """Run the blocking pipeline in a thread pool so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pipeline_service.run(triggered_by))


# ── Status ────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """
    Current pipeline state:
    - inbox_pending: files waiting to be processed
    - outbox_counts: files per category bucket
    - manifest: all-time stats
    - last_run: summary of the most recent run
    """
    return pipeline_service.get_status()


# ── Run History ───────────────────────────────────────────

@router.get("/runs")
async def get_runs(limit: int = Query(default=20, ge=1, le=100)):
    """Recent pipeline run history."""
    return {"runs": pipeline_service.get_runs(limit)}


# ── Outbox Inspection ─────────────────────────────────────

@router.get("/outbox/{category}")
async def list_outbox(category: str, limit: int = Query(default=50, ge=1, le=200)):
    """
    List processed files in a category outbox bucket.
    Returns claim numbers, confidence, PHI flag, and timestamps.
    """
    valid = {"inpatient", "outpatient", "pharmacy", "unknown", "review"}
    if category not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Choose from: {sorted(valid)}",
        )
    files = pipeline_service.list_outbox(category)
    return {
        "category": category,
        "count": len(files),
        "files": files[:limit],
    }


# ── Review Queue ──────────────────────────────────────────

@router.get("/review")
async def list_review_queue():
    """
    All documents pending human review (ambiguous or low-confidence classification).
    Each entry includes classifier_scores so the reviewer can see why it was flagged.
    """
    files = pipeline_service.list_review()
    return {"count": len(files), "files": files}


@router.post("/review/{filename}/assign")
async def assign_review(filename: str, body: AssignRequest):
    """
    Assign a document from the review queue to a category bucket.
    Moves the file from outbox/review/ → outbox/{target_category}/.
    """
    try:
        result = pipeline_service.assign_review(filename, body.target_category, body.assigned_by)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
