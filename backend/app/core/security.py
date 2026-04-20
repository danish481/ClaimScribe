"""
ClaimScribe AI - Security Module
HIPAA-aware security utilities for encryption, PHI detection, and access control
"""

import re
import hashlib
import hmac
from datetime import datetime
from typing import Optional, List

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import settings


# ── Encryption Manager ────────────────────────────────────

class EncryptionManager:
    """Handles AES-128 encryption for documents at rest."""

    def __init__(self):
        self._fernet = None
        self._init_cipher()

    def _init_cipher(self):
        """Initialize Fernet cipher from encryption key."""
        key = settings.ENCRYPTION_KEY or settings.SECRET_KEY[:32]
        # Ensure key is 32 bytes for Fernet
        if isinstance(key, str):
            key = key.encode()
        # Use PBKDF2 to derive a proper Fernet key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"claimscribe_salt_v1",
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        self._fernet = Fernet(derived_key)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt binary data."""
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt encrypted data."""
        return self._fernet.decrypt(token)

    def encrypt_string(self, text: str) -> str:
        """Encrypt a string and return base64-encoded result."""
        encrypted = self._fernet.encrypt(text.encode())
        return encrypted.decode()

    def decrypt_string(self, token: str) -> str:
        """Decrypt a base64-encoded encrypted string."""
        return self._fernet.decrypt(token.encode()).decode()


# ── PHI Detector ──────────────────────────────────────────

class PHIDetector:
    """Detects and masks Protected Health Information (PHI)."""

    # Regex patterns for common PHI elements
    PATTERNS = {
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "mrn": re.compile(r"\b(?:MRN|Medical Record|Number)[\s:#]*([A-Za-z0-9-]+)\b", re.IGNORECASE),
        "dob": re.compile(r"\b(?:DOB|Date of Birth|Birth Date)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", re.IGNORECASE),
        "account": re.compile(r"\b(?:Account|Claim|Policy)[\s:#]+([A-Za-z0-9-]+)\b", re.IGNORECASE),
    }

    @classmethod
    def detect_phi(cls, text: str) -> dict:
        """Detect PHI elements in text. Returns dict of found types."""
        findings = {}
        for phi_type, pattern in cls.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                findings[phi_type] = matches
        return findings

    @classmethod
    def mask_phi(cls, text: str, mask_char: str = "*") -> str:
        """Mask detected PHI in text."""
        masked = text
        for phi_type, pattern in cls.PATTERNS.items():
            if phi_type in ["ssn", "phone"]:
                masked = pattern.sub(lambda m: mask_char * len(m.group()), masked)
            elif phi_type == "email":
                masked = pattern.sub(lambda m: "[EMAIL-REDACTED]", masked)
            elif phi_type in ["mrn", "account"]:
                masked = pattern.sub(lambda m: f"{m.group().split()[0]} [REDACTED]", masked)
            elif phi_type == "dob":
                masked = pattern.sub(lambda m: "DOB: [REDACTED]", masked)
        return masked

    @classmethod
    def has_phi(cls, text: str) -> bool:
        """Quick check if text contains any PHI."""
        return bool(cls.detect_phi(text))


# ── Audit Logger ──────────────────────────────────────────

class AuditLogger:
    """HIPAA-compliant audit logging for all data access."""

    LOG_FILE = None  # Set during initialization

    @classmethod
    def log_event(
        cls,
        event_type: str,
        user_id: str = "anonymous",
        resource_type: str = "",
        resource_id: str = "",
        details: Optional[dict] = None,
        ip_address: str = "",
    ):
        """Log an auditable event."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "user_id": cls._hash_identifier(user_id),
            "resource_type": resource_type,
            "resource_id": cls._hash_identifier(resource_id),
            "details": details or {},
            "ip_address": ip_address,
        }
        # In production, write to secure audit log store
        # For demo: print structured log
        import json
        print(f"[AUDIT] {json.dumps(entry)}")
        return entry

    @staticmethod
    def _hash_identifier(identifier: str) -> str:
        """Create a hashed version of an identifier for privacy."""
        if not identifier:
            return ""
        return hashlib.sha256(f"{identifier}_claimscribe_salt".encode()).hexdigest()[:16]


# ── Convenience Instance ──────────────────────────────────
encryption = EncryptionManager()
