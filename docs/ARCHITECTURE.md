# ClaimScribe AI — Architecture

## System Overview

ClaimScribe AI is a single-tenant, containerized document intelligence platform. On Render free tier, two services run: a FastAPI backend (Docker) and a React static site (CDN). The backend embeds MLflow using a local file store, eliminating the need for a third container.

```
  Browser
     │
     │ HTTPS (Render CDN)
     ▼
┌─────────────────────┐
│  React Frontend     │  Static site served from Render's CDN
│  (Vite + Tailwind)  │  API calls go to backend via VITE_API_URL
└────────┬────────────┘
         │ HTTPS REST
         ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI Backend (Docker)              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  /documents │  │  /llm/query  │  │  /health  │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                │                │         │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌────▼──────┐  │
│  │  Document   │  │  LLM Service │  │  MLflow   │  │
│  │  Processor  │  │  (Gemini /   │  │  Tracker  │  │
│  │  + OCR      │  │   mock)      │  │ (file://) │  │
│  └──────┬──────┘  └──────────────┘  └───────────┘  │
│         │                                           │
│  ┌──────▼──────┐  ┌─────────────┐  ┌────────────┐  │
│  │  Classifier │  │  PHI Detect │  │  Audit Log │  │
│  │ (keywords + │  │  + Encrypt  │  │  (HIPAA)   │  │
│  │  sklearn)   │  │  (Fernet)   │  │            │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────┘
         │                │                │
    /app/data/       SQLite meta      /app/data/
    uploads/                           mlruns/
```

## Data Flow

When a document arrives, it travels through a linear pipeline before a response is returned.

**Upload → Validate → Encrypt → OCR → PHI Detect → Classify → Structure → MLflow Log → Store → Respond**

The validator checks format and file size against `MAX_FILE_SIZE`. The `EncryptionManager` derives a Fernet key from the configured secret via PBKDF2-HMAC-SHA256 and writes the ciphertext to disk before any text extraction occurs — so raw document bytes never sit unencrypted on the filesystem, even transiently. OCR dispatches to the right extractor (`pytesseract` for images, `pdfplumber` + `pdf2image` fallback for PDFs, direct decode for text files). PHI detection runs regex patterns for SSNs, phone numbers, email addresses, MRNs, and dates of birth before the text leaves the security boundary. Classification and structured-data extraction follow, then metrics and artifacts are written to the MLflow file store. The processed metadata is held in an in-memory `DocumentStore` (replace with Postgres for production persistence).

## Classification Strategy

The classifier uses a weighted keyword scoring system across three claim types — INPATIENT, OUTPATIENT, and PHARMACY — with term weights ranging from 1.5 (general terms like "laboratory") to 5.0 (decisive terms like "inpatient", "pharmacy", "prescription"). After raw scores are accumulated, softmax normalization converts them to a probability distribution that sums to 1. The highest probability becomes the predicted type, provided it clears the configurable `CLASSIFICATION_CONFIDENCE_THRESHOLD` (default 0.6); below that, the document is classified as UNKNOWN. An ambiguity check compares the top two scores: if they are within 20% of each other, the confidence is penalized by 0.7× to signal uncertainty.

This keyword approach beats a pure supervised ML model in a bootstrap phase because no labeled training data exists yet. A model trained on zero examples cannot generalize; a carefully weighted keyword dictionary can be tuned by a domain expert in minutes and produces interpretable, auditable decisions — both HIPAA concerns. Once enough labeled documents accumulate, `classifier.train_ml_model()` trains a TF-IDF + Multinomial Naive Bayes sklearn pipeline and logs it to MLflow. At that point the system can migrate to ML-based scoring while keeping the keyword fallback as a safety net.

## HIPAA Safeguards

**Administrative controls** are implemented through `AuditLogger`, which logs every document upload, access, LLM query, and export event with a hashed user and resource identifier, event type, and ISO-8601 timestamp. The 7-year log retention policy matches the HIPAA minimum.

**Physical controls** are provided by container isolation: the backend runs as a non-root process inside a Docker container. On Render, containers are isolated at the hypervisor level. Uploaded files are encrypted before being written to disk and are never exposed via a public static file path.

**Technical controls** cover three areas: (1) Fernet symmetric encryption at rest for every uploaded document; (2) PHI masking in all LLM prompts — extracted text passes through `PHIDetector.mask_phi()` before being sent to the Gemini API, ensuring no SSNs or patient names leave the system in plaintext; (3) TLS in transit is enforced by Render's load balancer for all HTTPS connections.

## Scalability Path

The current architecture is deliberately minimal: one container, SQLite, in-memory document store, embedded MLflow file store. Each tier below represents a concrete next step.

**Free tier (current)** — Single Render Web Service, 512MB RAM, ephemeral disk, ~30s cold-start after 15 min idle. Suitable for demos and low-volume evaluation.

**Render Pro + Postgres** — Upgrade to a paid instance (no sleep), add a Render Postgres database, replace `DocumentStore` with SQLAlchemy + async Postgres, mount a Render Disk at `/app/data` for persistent uploads and MLflow artifacts. Zero infrastructure changes; just config and a Alembic migration.

**Azure Container Apps + Blob Storage** — Move the Docker image to Azure Container Registry, deploy to Azure Container Apps with horizontal autoscaling (1–10 replicas), replace local file storage with Azure Blob Storage via `aiofiles` + `azure-storage-blob`, point MLflow at a remote PostgreSQL backend store. Add Azure Key Vault for secrets rotation.

**Kubernetes + HPA** — Full production: GKE or AKS cluster, Horizontal Pod Autoscaler on CPU/memory, separate MLflow deployment with S3-compatible artifact store (MinIO or S3), Redis for caching classification results, Prometheus + Grafana for observability, cert-manager for TLS rotation.
