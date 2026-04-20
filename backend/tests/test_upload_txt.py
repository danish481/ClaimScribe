import io
import pytest
from app.models.schemas import ProcessingStatus

PHARMACY_CONTENT = (
    b"Prescription dispensed by PharmaCare Inc. NDC code 00093-0172. "
    b"Generic medication metformin, 30 days supply, 500mg tablet. "
    b"Dispensing fee applied. Refill count 2. Pharmacy benefit claim."
)


def test_upload_txt_pharmacy(client):
    r = client.post(
        "/api/v1/documents/upload",
        files={"file": ("claim.txt", io.BytesIO(PHARMACY_CONTENT), "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "document_id" in data
    assert data["document_id"] != ""
    assert data["confidence"] > 0
    assert data["detected_type"] == "pharmacy"


def test_upload_unsupported_format(client):
    r = client.post(
        "/api/v1/documents/upload",
        files={"file": ("claim.xyz", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == ProcessingStatus.FAILED.value
