"""
ClaimScribe AI - Pipeline Service
Automated batch ingestion: scan inbox → classify → redact → route to outbox buckets.

Flow:
  data/inbox/        ← drop zone (any supported format)
      ↓ SHA-256 dedup (pipeline.db)
  classify + PHI redact
      ↓
  data/outbox/inpatient/   ← team A
  data/outbox/outpatient/  ← team B
  data/outbox/pharmacy/    ← team C
      ↓ archive
  data/inbox_processed/
"""

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings, DATA_DIR
from app.core.security import PHIDetector, AuditLogger
from app.services.classifier import classifier
from app.services.ocr_service import ocr_service
from app.services.storage_adapters import get_storage_adapter

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".txt", ".docx"}

# Documents below this confidence OR flagged ambiguous go to review/
REVIEW_CONFIDENCE_THRESHOLD = 0.60


def _review_reason(is_ambiguous: bool, confidence: float) -> str:
    if is_ambiguous and confidence < REVIEW_CONFIDENCE_THRESHOLD:
        return f"Ambiguous classification and low confidence ({confidence:.0%})"
    if is_ambiguous:
        return f"Top two categories scored within 20% of each other ({confidence:.0%} confidence)"
    return f"Confidence below threshold ({confidence:.0%} < {REVIEW_CONFIDENCE_THRESHOLD:.0%})"

# Common healthcare claim number patterns
_CLAIM_PATTERNS = [
    re.compile(r"\bCLM[-\s]?(\d{5,12})\b", re.I),
    re.compile(r"\bClaim\s+(?:No|Number|#|ID)[:\s#]+([A-Z0-9][-A-Z0-9]{4,19})\b", re.I),
    re.compile(r"\b(?:CN|CLN)[:\s#]+([A-Z0-9][-A-Z0-9]{4,19})\b", re.I),
    re.compile(r"\b(\d{3}-\d{4}-\d{6})\b"),
    re.compile(r"\b(\d{3}-\d{2}-\d{5})\b"),
]


def _extract_claim_number(text: str) -> Optional[str]:
    for pat in _CLAIM_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


# ── Pipeline Database ──────────────────────────────────────

class PipelineDB:
    """SQLite manifest and run history (uses stdlib sqlite3, no ORM)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._bootstrap()

    def _cx(self) -> sqlite3.Connection:
        cx = sqlite3.connect(str(self.db_path), timeout=15, check_same_thread=False)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA journal_mode=WAL")
        return cx

    def _bootstrap(self):
        with self._cx() as cx:
            cx.executescript("""
                CREATE TABLE IF NOT EXISTS pipeline_manifest (
                    file_hash         TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    category          TEXT NOT NULL,
                    claim_number      TEXT,
                    confidence        REAL,
                    phi_detected      INTEGER DEFAULT 0,
                    output_uri        TEXT,
                    run_id            TEXT,
                    processed_at      TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id              TEXT PRIMARY KEY,
                    triggered_by        TEXT NOT NULL,
                    started_at          TEXT NOT NULL,
                    completed_at        TEXT,
                    files_found         INTEGER DEFAULT 0,
                    files_processed     INTEGER DEFAULT 0,
                    files_skipped       INTEGER DEFAULT 0,
                    files_failed        INTEGER DEFAULT 0,
                    counts_by_category  TEXT DEFAULT '{}',
                    errors              TEXT DEFAULT '[]',
                    status              TEXT DEFAULT 'running'
                );

                CREATE INDEX IF NOT EXISTS idx_manifest_hash
                    ON pipeline_manifest(file_hash);
                CREATE INDEX IF NOT EXISTS idx_manifest_category
                    ON pipeline_manifest(category);
                CREATE INDEX IF NOT EXISTS idx_runs_started
                    ON pipeline_runs(started_at DESC);
            """)

    def is_processed(self, file_hash: str) -> bool:
        with self._cx() as cx:
            return cx.execute(
                "SELECT 1 FROM pipeline_manifest WHERE file_hash=?", (file_hash,)
            ).fetchone() is not None

    def record_file(
        self, file_hash: str, filename: str, category: str,
        claim_number: Optional[str], confidence: float,
        phi_detected: bool, output_uri: str, run_id: str,
    ):
        with self._cx() as cx:
            cx.execute("""
                INSERT OR REPLACE INTO pipeline_manifest
                (file_hash, original_filename, category, claim_number, confidence,
                 phi_detected, output_uri, run_id, processed_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                file_hash, filename, category, claim_number, confidence,
                int(phi_detected), output_uri, run_id,
                datetime.utcnow().isoformat(),
            ))

    def create_run(self, run_id: str, triggered_by: str):
        with self._cx() as cx:
            cx.execute(
                "INSERT INTO pipeline_runs (run_id, triggered_by, started_at) VALUES (?,?,?)",
                (run_id, triggered_by, datetime.utcnow().isoformat()),
            )

    def complete_run(
        self, run_id: str, files_found: int, files_processed: int,
        files_skipped: int, files_failed: int,
        counts_by_category: Dict, errors: List[str],
    ):
        status = "completed" if files_failed == 0 else "completed_with_errors"
        with self._cx() as cx:
            cx.execute("""
                UPDATE pipeline_runs SET
                  completed_at=?, files_found=?, files_processed=?,
                  files_skipped=?, files_failed=?,
                  counts_by_category=?, errors=?, status=?
                WHERE run_id=?
            """, (
                datetime.utcnow().isoformat(), files_found, files_processed,
                files_skipped, files_failed,
                json.dumps(counts_by_category), json.dumps(errors), status,
                run_id,
            ))

    def get_runs(self, limit: int = 20) -> List[Dict]:
        with self._cx() as cx:
            rows = cx.execute(
                "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["counts_by_category"] = json.loads(d.get("counts_by_category") or "{}")
                d["errors"] = json.loads(d.get("errors") or "[]")
                result.append(d)
            return result

    def update_category(self, file_hash: str, new_category: str, new_output_uri: str):
        with self._cx() as cx:
            cx.execute(
                "UPDATE pipeline_manifest SET category=?, output_uri=? WHERE file_hash=?",
                (new_category, new_output_uri, file_hash),
            )

    def manifest_stats(self) -> Dict:
        with self._cx() as cx:
            total = cx.execute("SELECT COUNT(*) FROM pipeline_manifest").fetchone()[0]
            rows = cx.execute(
                "SELECT category, COUNT(*) cnt FROM pipeline_manifest GROUP BY category"
            ).fetchall()
            return {
                "total_processed_ever": total,
                "by_category": {r["category"]: r["cnt"] for r in rows},
            }


# ── Pipeline Service ───────────────────────────────────────

class PipelineService:
    """
    Scan inbox → classify → PHI-redact → route to per-category outbox.
    Hash-based dedup means a file is never processed twice.
    """

    def __init__(self):
        self.inbox_dir = DATA_DIR / "inbox"
        self.outbox_dir = DATA_DIR / "outbox"
        self.archive_dir = DATA_DIR / "inbox_processed"
        self.db = PipelineDB(DATA_DIR / "pipeline.db")
        self.storage = get_storage_adapter(self.outbox_dir)
        self._ensure_dirs()
        self._last_run: Optional[Dict] = None

    def _ensure_dirs(self):
        for d in (self.inbox_dir, self.archive_dir):
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def scan_inbox(self) -> List[Path]:
        """All unarchived supported files in inbox, oldest first."""
        return sorted(
            (p for p in self.inbox_dir.iterdir()
             if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS),
            key=lambda p: p.stat().st_mtime,
        )

    # ── Main entry point ──────────────────────────────────

    def run(self, triggered_by: str = "schedule") -> Dict:
        """Execute one full pipeline pass. Returns run summary dict."""
        run_id = uuid.uuid4().hex[:8]
        self.db.create_run(run_id, triggered_by)

        inbox_files = self.scan_inbox()
        files_found = len(inbox_files)
        files_processed = files_skipped = files_failed = 0
        counts_by_category: Dict[str, int] = {}
        errors: List[str] = []

        for file_path in inbox_files:
            try:
                if not file_path.exists():
                    files_skipped += 1
                    continue
                file_hash = self._hash_file(file_path)

                if self.db.is_processed(file_hash):
                    files_skipped += 1
                else:
                    result = self._process_file(file_path, file_hash, run_id)
                    cat = result["category"]
                    counts_by_category[cat] = counts_by_category.get(cat, 0) + 1
                    files_processed += 1

                # Archive regardless (keep inbox clean)
                # FileNotFoundError means a concurrent run already moved this file — safe to ignore
                try:
                    archive_dest = self.archive_dir / file_path.name
                    if archive_dest.exists():
                        archive_dest = self.archive_dir / f"{file_hash[:8]}_{file_path.name}"
                    file_path.rename(archive_dest)
                except FileNotFoundError:
                    pass

            except Exception as exc:
                files_failed += 1
                errors.append(f"{file_path.name}: {exc}")
                print(f"[Pipeline] Error — {file_path.name}: {exc}")

        self.db.complete_run(
            run_id, files_found, files_processed,
            files_skipped, files_failed, counts_by_category, errors,
        )

        summary = {
            "run_id": run_id,
            "triggered_by": triggered_by,
            "files_found": files_found,
            "files_processed": files_processed,
            "files_skipped": files_skipped,
            "files_failed": files_failed,
            "counts_by_category": counts_by_category,
            "errors": errors,
        }
        self._last_run = summary

        AuditLogger.log_event(
            event_type="pipeline_run_completed",
            details=summary,
        )
        return summary

    def _process_file(self, file_path: Path, file_hash: str, run_id: str) -> Dict:
        """OCR → classify → PHI redact → write to outbox."""
        # 1. Read raw bytes + extract text
        raw = file_path.read_bytes()
        ext = file_path.suffix.lstrip(".")
        text = ocr_service.extract_text(raw, ext)

        # 2. Classify
        clf = classifier.classify(text, document_id=file_hash[:12])
        category: str = clf["predicted_type"].value
        confidence: float = clf["confidence"]

        # 3. PHI detection + masking
        phi_findings = PHIDetector.detect_phi(text)
        phi_detected = bool(phi_findings)
        redacted_text = PHIDetector.mask_phi(text) if phi_detected else text

        # 4. Extract claim number (before masking to catch it)
        claim_number = _extract_claim_number(text) or f"UNKNOWN-{file_hash[:8].upper()}"

        # 5. Decide routing: ambiguous or low-confidence → review queue
        is_ambiguous: bool = clf.get("is_ambiguous", False)
        needs_review = is_ambiguous or confidence < REVIEW_CONFIDENCE_THRESHOLD
        routed_to = "review" if needs_review else category

        # 6. Build output payload (PHI-free)
        payload = {
            "claim_number": claim_number,
            "category": category,           # classifier's best guess
            "routed_to": routed_to,         # actual bucket
            "needs_review": needs_review,
            "review_reason": _review_reason(is_ambiguous, confidence) if needs_review else None,
            "confidence": round(confidence, 4),
            "classifier_scores": clf.get("scores", {}),
            "source_file": file_path.name,
            "file_hash": file_hash,
            "phi_detected": phi_detected,
            "phi_types_found": list(phi_findings.keys()) if phi_detected else [],
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_run_id": run_id,
            "redacted_text": redacted_text,
            "assigned_by": None,
            "assigned_at": None,
        }

        # 7. Write to chosen bucket
        out_filename = f"{claim_number}_{file_path.stem}.json"
        output_uri = self.storage.write_outbox(routed_to, out_filename, payload)

        # 8. Record in manifest
        self.db.record_file(
            file_hash, file_path.name, routed_to, claim_number,
            confidence, phi_detected, output_uri, run_id,
        )

        return {"category": routed_to, "claim_number": claim_number, "output_uri": output_uri, "needs_review": needs_review}

    # ── Status & History ──────────────────────────────────

    def get_status(self) -> Dict:
        return {
            "inbox_pending": len(self.scan_inbox()),
            "outbox_counts": self.storage.outbox_counts(),
            "manifest": self.db.manifest_stats(),
            "last_run": self._last_run,
            "schedule_interval_minutes": settings.PIPELINE_SCHEDULE_MINUTES,
            "storage_backend": settings.PIPELINE_STORAGE_BACKEND,
        }

    def get_runs(self, limit: int = 20) -> List[Dict]:
        return self.db.get_runs(limit)

    def list_outbox(self, category: str) -> List[Dict]:
        return self.storage.list_outbox(category)

    def list_review(self) -> List[Dict]:
        """All files currently sitting in the review queue."""
        return self.storage.list_outbox("review", limit=200)

    def assign_review(self, filename: str, target_category: str, assigned_by: str = "reviewer") -> Dict:
        """
        Move a file from review/ to a real category bucket.
        Updates the JSON payload so the assignment is recorded inside the file.
        """
        valid = {"inpatient", "outpatient", "pharmacy"}
        if target_category not in valid:
            raise ValueError(f"target_category must be one of {valid}")

        review_dir = self.outbox_dir / "review"
        src = review_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"{filename} not found in review queue")

        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["routed_to"] = target_category
        payload["needs_review"] = False
        payload["assigned_by"] = assigned_by
        payload["assigned_at"] = datetime.utcnow().isoformat() + "Z"

        # Write to target bucket
        output_uri = self.storage.write_outbox(target_category, filename, payload)

        # Remove from review
        src.unlink()

        # Update manifest
        self.db.update_category(payload["file_hash"], target_category, output_uri)

        AuditLogger.log_event(
            event_type="review_assigned",
            details={"filename": filename, "assigned_to": target_category, "by": assigned_by},
        )
        return {"filename": filename, "assigned_to": target_category, "output_uri": output_uri}


# ── Singleton ──────────────────────────────────────────────
pipeline_service = PipelineService()
