"""
ClaimScribe AI - Storage Adapters
Pluggable storage backend: Local filesystem today, S3/GCS tomorrow.
Swap the adapter in config (PIPELINE_STORAGE_BACKEND) without touching pipeline logic.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict


class BaseStorageAdapter(ABC):
    """Abstract storage interface — all adapters implement this."""

    @abstractmethod
    def write_outbox(self, category: str, filename: str, payload: dict) -> str:
        """Write a processed document payload to the category bucket. Returns destination URI."""

    @abstractmethod
    def list_outbox(self, category: str, limit: int = 50) -> List[Dict]:
        """List recent files in a category bucket."""

    @abstractmethod
    def outbox_counts(self) -> Dict[str, int]:
        """Return file count per category bucket."""


# ── Local Filesystem Adapter ───────────────────────────────

class LocalStorageAdapter(BaseStorageAdapter):
    """Stores outputs in data/outbox/{category}/ on the local filesystem."""

    CATEGORIES = ("inpatient", "outpatient", "pharmacy", "unknown", "review")

    def __init__(self, outbox_root: Path):
        self.outbox_root = outbox_root
        for cat in self.CATEGORIES:
            (outbox_root / cat).mkdir(parents=True, exist_ok=True)

    def write_outbox(self, category: str, filename: str, payload: dict) -> str:
        dest = self.outbox_root / category / filename
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return str(dest)

    def list_outbox(self, category: str, limit: int = 50) -> List[Dict]:
        cat_dir = self.outbox_root / category
        if not cat_dir.exists():
            return []
        files = sorted(cat_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        result = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result.append({
                    "filename": f.name,
                    "claim_number": data.get("claim_number"),
                    "source_file": data.get("source_file"),
                    "confidence": data.get("confidence"),
                    "phi_detected": data.get("phi_detected"),
                    "processed_at": data.get("processed_at"),
                })
            except Exception:
                pass
        return result

    def outbox_counts(self) -> Dict[str, int]:
        return {
            cat: len(list((self.outbox_root / cat).glob("*.json")))
            for cat in self.CATEGORIES
            if (self.outbox_root / cat).exists()
        }


# ── S3 Adapter (stub — fill in boto3 calls for production) ─

class S3StorageAdapter(BaseStorageAdapter):
    """
    AWS S3 adapter. Each category maps to a prefix in the configured bucket.
    Install boto3 and set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars.
    """

    def __init__(self, bucket: str, prefix: str = "claimscribe/outbox"):
        self.bucket = bucket
        self.prefix = prefix
        # import boto3
        # self._s3 = boto3.client("s3")

    def write_outbox(self, category: str, filename: str, payload: dict) -> str:
        key = f"{self.prefix}/{category}/{filename}"
        # self._s3.put_object(
        #     Bucket=self.bucket, Key=key,
        #     Body=json.dumps(payload, indent=2).encode(),
        #     ContentType="application/json",
        # )
        return f"s3://{self.bucket}/{key}"

    def list_outbox(self, category: str, limit: int = 50) -> List[Dict]:
        raise NotImplementedError(
            "S3StorageAdapter.list_outbox is not implemented. "
            "Uncomment the boto3 calls and install boto3 to use S3 storage."
        )

    def outbox_counts(self) -> Dict[str, int]:
        raise NotImplementedError(
            "S3StorageAdapter.outbox_counts is not implemented. "
            "Uncomment the boto3 calls and install boto3 to use S3 storage."
        )


# ── GCS Adapter (stub) ─────────────────────────────────────

class GCSStorageAdapter(BaseStorageAdapter):
    """
    Google Cloud Storage adapter. Requires google-cloud-storage package.
    Set GOOGLE_APPLICATION_CREDENTIALS env var.
    """

    def __init__(self, bucket: str, prefix: str = "claimscribe/outbox"):
        self.bucket = bucket
        self.prefix = prefix

    def write_outbox(self, category: str, filename: str, payload: dict) -> str:
        return f"gs://{self.bucket}/{self.prefix}/{category}/{filename}"

    def list_outbox(self, category: str, limit: int = 50) -> List[Dict]:
        raise NotImplementedError(
            "GCSStorageAdapter.list_outbox is not implemented. "
            "Install google-cloud-storage and implement GCS calls to use GCS storage."
        )

    def outbox_counts(self) -> Dict[str, int]:
        raise NotImplementedError(
            "GCSStorageAdapter.outbox_counts is not implemented. "
            "Install google-cloud-storage and implement GCS calls to use GCS storage."
        )


# ── Factory ────────────────────────────────────────────────

def get_storage_adapter(outbox_root: Path) -> BaseStorageAdapter:
    """Return the configured storage adapter."""
    from app.config import settings
    backend = getattr(settings, "PIPELINE_STORAGE_BACKEND", "local")
    if backend == "s3":
        return S3StorageAdapter(bucket=settings.PIPELINE_S3_BUCKET)
    if backend == "gcs":
        return GCSStorageAdapter(bucket=settings.PIPELINE_GCS_BUCKET)
    return LocalStorageAdapter(outbox_root)
