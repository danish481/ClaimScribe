import pytest
from app.services.classifier import classifier
from app.models.schemas import DocumentType

INPATIENT_TEXT = (
    "Patient admitted to ICU. Hospital stay 5 days. Discharge summary attached. "
    "Attending physician Dr. Smith. Room and board charges included."
)
OUTPATIENT_TEXT = (
    "Office visit clinic consultation. Follow-up diagnostic test ordered. "
    "Outpatient procedure completed same day. No admission required."
)
PHARMACY_TEXT = (
    "Prescription dispensed. NDC code 00093-0172. Generic medication, 30 days supply. "
    "Refill authorized. Dispensing fee applied."
)


def test_classify_inpatient():
    result = classifier.classify(INPATIENT_TEXT)
    assert result["predicted_type"] == DocumentType.INPATIENT
    assert result["confidence"] > 0.3


def test_classify_outpatient():
    result = classifier.classify(OUTPATIENT_TEXT)
    assert result["predicted_type"] == DocumentType.OUTPATIENT
    assert result["confidence"] > 0.3


def test_classify_pharmacy():
    result = classifier.classify(PHARMACY_TEXT)
    assert result["predicted_type"] == DocumentType.PHARMACY
    assert result["confidence"] > 0.3


def test_classify_returns_required_keys():
    result = classifier.classify(INPATIENT_TEXT)
    for key in ("predicted_type", "confidence", "scores", "method", "is_ambiguous"):
        assert key in result
