# ClaimScribe AI — Healthcare Document Intelligence Platform

> **Automated Document Ingestion, Classification & Batch Pipeline for Health Insurance Claims**

ClaimScribe AI is a production-grade, HIPAA-aware document intelligence platform that automates the ingestion, classification, PHI redaction, and AI-powered analysis of health insurance claims documents. Built for scalability, compliance, and real-world deployment.

---

## Project Objectives

| # | Objective | Status | How It's Met |
|---|-----------|--------|--------------|
| 1 | **Automate ingestion of diverse document formats with minimal manual intervention** | ✅ Complete | Batch pipeline scans `data/inbox/` every 30 min (APScheduler). Supports PDF, PNG, JPG, TIFF, DOCX, TXT. SHA-256 dedup prevents reprocessing. Manual trigger via UI or API. Zero human touch needed for standard documents. |
| 2 | **Accurately classify claims into predefined categories** | ✅ Complete | Weighted keyword classifier (inpatient / outpatient / pharmacy) with MLflow-tracked confidence scores. Ambiguous or low-confidence documents (< 60% or second category ≥ 25% of top) are routed to a human review queue instead of being forced into the wrong bucket. |
| 3 | **Ensure compliance with data privacy and security standards** | ✅ Complete | Fernet AES-128 encryption at rest, regex-based PHI detection & masking (SSN, DOB, MRN, phone, email) before any output is written, HIPAA-compliant audit log on every event, no raw PHI in outbox JSON files. |
| 4 | **Provide real-time monitoring and alerting for ingestion failures or classification errors** | ✅ Complete | `/api/v1/health/status` reports component health. `/api/v1/monitoring/metrics` exposes processing stats. Pipeline run history records per-run error lists. MLflow logs confidence and processing time per classification. Review queue surfaces ambiguous documents for human attention. |
| 5 | **Enable scalability to handle increasing claim volumes** | ✅ Complete | Fully containerised (Docker Compose). Stateless FastAPI backend — add replicas behind a load balancer without code changes. Storage abstraction layer swaps local → S3/GCS with one env var. APScheduler interval configurable. SQLite swappable for PostgreSQL via `DATABASE_URL`. |

---

## Features

- **Multi-Format Document Ingestion** — PDFs, scanned images, TIFFs, PNGs, JPEGs, TXT, DOCX
- **AI-Powered Classification** — Automatically classifies into `inpatient`, `outpatient`, `pharmacy`
- **OCR + Text Extraction** — Tesseract OCR for scanned documents, direct text extraction from digital PDFs
- **Healthcare LLM Assistant** — Domain-specific AI queries on extracted document data (Gemini 2.5 Flash)
- **Batch Ingestion Pipeline** — Drop files into `data/inbox/`, pipeline auto-classifies, PHI-redacts, and routes to per-team outbox buckets on a schedule or manual trigger
- **Structured Data Export** — Pandas DataFrame with inferred columns for downstream analytics
- **MLflow Integration** — Full model versioning, experiment tracking, and metric logging
- **HIPAA Compliance Layer** — Fernet encryption, audit logging, PHI detection & masking
- **Real-Time Monitoring** — System health, processing metrics, failure alerts
- **Responsive Web UI** — 5-tab SaaS interface: Upload, Documents, AI Assistant, Analytics, Pipeline

---

## Architecture

```
                    ┌──────────────────────┐
                    │    React Frontend     │
                    │  (Vite + TypeScript)  │
                    │  localhost:5174       │
                    └──────────┬───────────┘
                               │ HTTP
          ┌────────────────────┼────────────────────┐
          │                    │                    │
 ┌────────▼────────┐  ┌────────▼────────┐  ┌───────▼───────┐
 │  Upload + OCR   │  │   LLM Chat      │  │  Pipeline UI  │
 │  (5 formats)    │  │  (Gemini 2.5)   │  │  (Run Now)    │
 └────────┬────────┘  └────────┬────────┘  └───────┬───────┘
          │                    │                    │
 ┌────────▼────────────────────▼────────────────────▼───────┐
 │                   FastAPI Backend  :8001                  │
 │  ┌─────────────┐ ┌─────────────┐ ┌──────┐ ┌──────────┐  │
 │  │  Document   │ │  Pipeline   │ │ LLM  │ │  MLflow  │  │
 │  │  Processor  │ │  Service    │ │ Svc  │ │  Tracker │  │
 │  └─────────────┘ └─────────────┘ └──────┘ └──────────┘  │
 │  ┌─────────────┐ ┌─────────────┐ ┌──────┐ ┌──────────┐  │
 │  │  HIPAA PHI  │ │  Keyword    │ │Audit │ │APScheduler│  │
 │  │  Detector   │ │  Classifier │ │ Log  │ │(30min)   │  │
 │  └─────────────┘ └─────────────┘ └──────┘ └──────────┘  │
 └───────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼──────────────────────┐
          ▼                    ▼                      ▼
 ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────┐
 │  MLflow Server  │  │    SQLite    │  │   data/ (bind mount) │
 │  :5001          │  │  (metadata)  │  │  inbox/  outbox/     │
 └─────────────────┘  └──────────────┘  └─────────────────────┘
```

### Batch Pipeline Flow

```
data/inbox/              ← drop any PDF / image / TXT here
     │
     ▼  SHA-256 dedup (never reprocesses the same file)
     │
     ▼  OCR → Classify → PHI Redact → Extract claim number
     │
     ├──► data/outbox/inpatient/   ← Team A  (JSON, PHI masked)
     ├──► data/outbox/outpatient/  ← Team B
     └──► data/outbox/pharmacy/    ← Team C
               │
               ▼
     data/inbox_processed/        ← originals archived
```

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Docker Desktop** | Includes Docker Engine + Compose — the only runtime dependency |
| **Git** | To clone the repository |
| **RAM** | 4 GB minimum, 8 GB recommended |
| **Disk** | ~3 GB for Docker images on first build |

---

### macOS

```bash
# 1. Install Docker Desktop
brew install --cask docker          # or download from docker.com
open -a Docker                      # start Docker Desktop, wait for whale icon

# 2. Clone
git clone https://github.com/danish481/ClaimScribe.git
cd claimscribe-ai

# 3. Configure environment
cp .env.example .env
# Optional: set your Gemini key for AI assistant
nano .env                           # or open in any editor

# 4. Build and start (first run ~5 min, cached thereafter ~30 s)
docker compose up --build

# 5. Drop documents into the pipeline inbox
cp ~/Downloads/my_claim.pdf data/inbox/
```

### Windows (PowerShell or Git Bash)

```powershell
# 1. Install Docker Desktop from docker.com/products/docker-desktop
#    After install: open Docker Desktop from Start Menu, wait for status "Engine running"

# 2. Clone (Git Bash or PowerShell)
git clone https://github.com/danish481/ClaimScribe.git
cd claimscribe-ai

# 3. Configure environment
copy .env.example .env
# Optional: open .env in Notepad/VS Code and set GEMINI_API_KEY

# 4. Build and start
docker compose up --build

# 5. Drop documents into the pipeline inbox
copy C:\Downloads\my_claim.pdf data\inbox\
```

> **Windows tip:** If you see `Error: failed to connect to Docker daemon` — Docker Desktop is not running. Open it from the Start Menu and wait ~30 seconds for the engine to start before retrying.

### Linux (Ubuntu / Debian)

```bash
# 1. Install Docker Engine + Compose plugin
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER       # allow running docker without sudo
newgrp docker                       # apply group change without logout

# 2. Clone
git clone https://github.com/danish481/ClaimScribe.git
cd claimscribe-ai

# 3. Configure environment
cp .env.example .env
# Optional: set GEMINI_API_KEY
nano .env

# 4. Build and start
docker compose up --build

# 5. Drop documents into the pipeline inbox
cp ~/downloads/my_claim.pdf data/inbox/
```

---

### Services After Startup

| Service | URL | Notes |
|---------|-----|-------|
| Frontend UI | http://localhost:5174 | Main web interface |
| Backend API + Swagger | http://localhost:8001/docs | Interactive API docs |
| MLflow Experiment Tracker | http://localhost:5001 | Classification metrics & run history |

> **MLflow UI:** Open http://localhost:5001 and select the `claimscribe-document-classification` experiment to see all classification runs, confidence scores, and per-document metrics.

---

### Environment Variables (`.env`)

Copy `.env.example` to `.env` before starting. All variables are optional except `GEMINI_API_KEY` for the AI assistant:

```env
# AI Assistant (optional — built-in fallback responses work without this)
GEMINI_API_KEY=your_key_here        # get free key at aistudio.google.com

# Security (auto-generated if not set — set explicitly for persistent encryption)
SECRET_KEY=change-me-in-production
ENCRYPTION_KEY=                     # leave blank to auto-derive from SECRET_KEY

# Pipeline
PIPELINE_SCHEDULE_MINUTES=30        # how often batch pipeline fires
PIPELINE_STORAGE_BACKEND=local      # local | s3 | gcs

# S3 (only needed if PIPELINE_STORAGE_BACKEND=s3)
PIPELINE_S3_BUCKET=my-claims-bucket
```

---

### Stopping and Restarting

```bash
# Stop all services (data is preserved in data/ folder)
docker compose down

# Restart without rebuilding (fast)
docker compose up

# Full rebuild (after code changes)
docker compose up --build

# View logs
docker compose logs -f backend      # backend logs
docker compose logs -f frontend     # frontend logs
docker compose logs -f mlflow       # MLflow server logs
```

---

### Using the Pipeline

```bash
# Drop any supported document into the inbox
cp my_claim.pdf       data/inbox/    # PDF
cp scan.png           data/inbox/    # scanned image
cp claim_note.txt     data/inbox/    # plain text
cp discharge_summary.docx data/inbox/

# Option A — automatic: scheduler fires every 30 minutes
# Option B — trigger immediately via UI: Pipeline tab → Run Now
# Option C — trigger via API:
curl -X POST http://localhost:8001/api/v1/pipeline/trigger

# Windows PowerShell equivalent:
Invoke-RestMethod -Method POST -Uri http://localhost:8001/api/v1/pipeline/trigger
```

Processed outputs appear in `data/outbox/{inpatient|outpatient|pharmacy|review}/` as JSON files. Ambiguous or low-confidence documents (< 60%) land in `review/` for human assignment via the Pipeline tab.

---

## Deploy to Render.com (Free, Public URL)

The repo includes a `render.yaml` blueprint for one-click deploy:

1. Push this repo to GitHub.
2. On Render: **New → Blueprint → select this repo**. Render reads `render.yaml` and provisions both services automatically.
3. Set these env vars in the Render dashboard after first deploy:
   - `GEMINI_API_KEY` on `claimscribe-backend` — get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey)
   - `CORS_ORIGINS` on `claimscribe-backend` → your frontend URL, e.g. `https://claimscribe-frontend.onrender.com`
   - `VITE_API_URL` on `claimscribe-frontend` → your backend URL, e.g. `https://claimscribe-backend.onrender.com`
4. Redeploy both services. Your shareable URL is the frontend `.onrender.com` link.

**Free-tier caveats:**
- Backend spins down after 15 min idle; first request takes ~30 s to wake.
- Ephemeral storage — uploads and MLflow runs reset on redeploy. Add a Render Disk (paid) mounted at `/app/data` for persistence.
- MLflow UI is not exposed publicly on free tier. Access experiment data via `GET /api/v1/documents/metrics/classifier`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS + Vite |
| Backend | FastAPI + Python 3.11 |
| OCR | Tesseract OCR + pdfplumber + Pillow |
| LLM | Google Gemini 2.5 Flash |
| Scheduler | APScheduler (background cron inside FastAPI) |
| ML Tracking | MLflow 2.12 |
| Storage Adapter | Local filesystem (swap to S3/GCS via config) |
| Database | SQLite (document metadata + pipeline manifest) |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Security | Fernet encryption, PHI detection, HIPAA audit logging |

---

## Project Structure

```
claimscribe-ai/
├── docker-compose.yml
├── render.yaml                     # Render.com one-click deploy blueprint
├── .env                            # Local secrets (not committed)
├── data/                           # Bind-mounted into containers
│   ├── inbox/                      ← DROP FILES HERE for pipeline
│   ├── outbox/
│   │   ├── inpatient/              ← Team A output bucket
│   │   ├── outpatient/             ← Team B output bucket
│   │   └── pharmacy/               ← Team C output bucket
│   ├── inbox_processed/            ← archived originals
│   ├── uploads/                    ← single-doc upload storage
│   ├── exports/                    ← CSV/Excel exports
│   └── mlruns/                     ← MLflow experiment data
├── .github/workflows/
│   └── ci-cd.yml                   # GitHub Actions: lint → test → build → deploy
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI entry point + APScheduler startup
│       ├── config.py               # All settings via environment variables
│       ├── models/
│       │   └── schemas.py          # Pydantic request/response models
│       ├── routers/
│       │   ├── documents.py        # Upload, list, export endpoints
│       │   ├── llm.py              # LLM query endpoints
│       │   ├── health.py           # Health + metrics endpoints
│       │   └── pipeline.py         # Pipeline trigger, status, outbox endpoints
│       ├── services/
│       │   ├── document_processor.py
│       │   ├── classifier.py       # Keyword-based + MLflow-tracked classifier
│       │   ├── llm_service.py      # Gemini 2.5 Flash integration
│       │   ├── ocr_service.py      # Tesseract + pdfplumber
│       │   ├── mlflow_tracker.py
│       │   ├── pipeline_service.py # Batch ingestion engine + SQLite manifest
│       │   └── storage_adapters.py # Local / S3 / GCS storage abstraction
│       └── core/
│           ├── security.py         # Encryption, PHI detector, audit logger
│           └── audit_logger.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx                 # 5-tab layout
        └── components/
            ├── Hero.tsx
            ├── UploadSection.tsx   # Single document upload + camera capture
            ├── Dashboard.tsx       # Document list + detail panel + Analyze with AI
            ├── LLMChat.tsx         # Gemini-powered chat (auto-analyzes selected doc)
            ├── AnalyticsPanel.tsx  # Charts and classification stats
            └── PipelinePanel.tsx   # Inbox/outbox status, run history, Run Now button
```

---

## API Endpoints

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload & process a document |
| POST | `/api/v1/documents/capture` | Process camera-captured image |
| GET | `/api/v1/documents/` | List all processed documents |
| GET | `/api/v1/documents/{id}` | Get full document detail |
| POST | `/api/v1/documents/{id}/export` | Export as CSV / Excel / JSON |
| GET | `/api/v1/documents/export/{export_id}/download` | Download export file |

### LLM
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/llm/query` | Send a healthcare AI query (optionally with document IDs) |
| GET | `/api/v1/llm/conversations` | List conversation history |

### Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipeline/trigger` | Manually trigger a pipeline run |
| GET | `/api/v1/pipeline/status` | Inbox count, outbox counts, last run summary |
| GET | `/api/v1/pipeline/runs` | Run history (last N runs) |
| GET | `/api/v1/pipeline/outbox/{category}` | List files in a category outbox |

### Health & Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/status` | Full system health check |
| GET | `/api/v1/monitoring/metrics` | Processing metrics |

Full interactive docs: **http://localhost:8001/docs**

---

## Pipeline Output Format

Each processed document produces a JSON file in the appropriate outbox bucket:

```json
{
  "claim_number": "CLM-2024-001234",
  "category": "inpatient",
  "confidence": 0.97,
  "source_file": "hospital_claim_jan.pdf",
  "file_hash": "0f7695...",
  "phi_detected": true,
  "phi_types_found": ["ssn", "dob"],
  "processed_at": "2026-04-21T08:00:00Z",
  "pipeline_run_id": "f77ed037",
  "redacted_text": "HOSPITAL ADMISSION CLAIM\nClaim #: CLM-2024-001234\n[PHI REDACTED]...",
  "classifier_scores": {
    "inpatient": 0.97,
    "outpatient": 0.02,
    "pharmacy": 0.01
  }
}
```

To switch output to S3 or GCS, set in `.env`:
```env
PIPELINE_STORAGE_BACKEND=s3
PIPELINE_S3_BUCKET=my-claims-bucket
```

---

## Security & HIPAA Considerations

- **Encryption at Rest** — All uploaded documents encrypted with Fernet (AES-128 derived key)
- **PHI Detection & Masking** — Automatic regex-based detection of SSN, DOB, MRN, phone, email; masked before any output
- **Audit Logging** — Every upload, query, classification, and pipeline run is logged with timestamp
- **Deduplication** — SHA-256 content hashing ensures no document is processed twice
- **Data Retention** — Configurable auto-purge (`AUTO_PURGE_DAYS=90`)
- **No External Leak** — All OCR, classification, and PHI processing runs inside the containerized environment; only the LLM query goes to Google Gemini API

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key — omit to use built-in fallback responses |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `SECRET_KEY` | _(auto-generated)_ | App secret key |
| `ENCRYPTION_KEY` | _(auto-generated)_ | Fernet encryption key |
| `PIPELINE_SCHEDULE_MINUTES` | `30` | How often the batch pipeline fires |
| `PIPELINE_STORAGE_BACKEND` | `local` | `local`, `s3`, or `gcs` |
| `PIPELINE_S3_BUCKET` | _(empty)_ | S3 bucket name (if using s3 backend) |
| `CORS_ORIGINS` | `http://localhost:5174` | Allowed frontend origins |

---

## MLflow Experiment Tracking

Every classification is logged as an MLflow run:

- **Metrics**: confidence score, processing time, per-category scores
- **Parameters**: document ID, predicted type, ambiguity flag, text length
- **Artifacts**: text sample used for classification

Access the MLflow UI at **http://localhost:5001**

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`):

1. **Lint & Test** — `pytest` for backend, `tsc` type-check for frontend
2. **Security Scan** — Bandit for Python vulnerabilities
3. **Build & Push** — Docker image build
4. **Deploy** — Automated deployment to staging

---

## License

Proprietary — Built for case study demonstration purposes.
