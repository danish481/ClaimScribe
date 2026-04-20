import pytest
from app.core.security import PHIDetector

SSN = "123-45-6789"
EMAIL = "test@example.com"
PHONE = "(555) 123-4567"
MRN_TEXT = "MRN: 12345"


def test_detect_ssn():
    findings = PHIDetector.detect_phi(f"Patient SSN {SSN} on file.")
    assert "ssn" in findings


def test_detect_email():
    findings = PHIDetector.detect_phi(f"Contact {EMAIL} for details.")
    assert "email" in findings


def test_detect_phone():
    findings = PHIDetector.detect_phi(f"Call {PHONE} for appointment.")
    assert "phone" in findings


def test_detect_mrn():
    findings = PHIDetector.detect_phi(f"Record {MRN_TEXT} updated.")
    assert "mrn" in findings


def test_mask_phi_removes_ssn():
    text = f"Patient SSN {SSN} on file."
    masked = PHIDetector.mask_phi(text)
    assert SSN not in masked


def test_mask_phi_removes_email():
    text = f"Contact {EMAIL} for details."
    masked = PHIDetector.mask_phi(text)
    assert EMAIL not in masked


def test_has_phi_true():
    assert PHIDetector.has_phi(f"SSN: {SSN}") is True


def test_has_phi_false():
    assert PHIDetector.has_phi("No personal data here, just medical terms.") is False
