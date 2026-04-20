# ClaimScribe AI - Healthcare Document Intelligence Platform

> **Automated Document Ingestion & Classification for Health Insurance Claims Processing**

ClaimScribe AI is a production-grade, HIPAA-aware document intelligence platform that automates the ingestion, classification, and AI-powered analysis of health insurance claims documents. Built for scalability, compliance, and real-world deployment.

---

## Features

- **Multi-Format Document Ingestion** — PDFs, scanned images, TIFFs, PNGs, JPEGs, faxed documents
- **AI-Powered Classification** — Automatically classifies into `inpatient`, `outpatient`, `pharmacy`
- **OCR + Text Extraction** — Tesseract OCR for scanned documents, direct text extraction from digital PDFs
- **Healthcare LLM Assistant** — Domain-specific AI queries on extracted document data (Gemini-powered)
- **Structured Data Export** — Pandas DataFrame with inferred columns for downstream analytics
- **MLflow Integration** — Full model versioning, experiment tracking, and metric logging
- **HIPAA Compliance Layer** — Encryption, audit logging, PHI detection, secure data handling
- **Real-Time Monitoring** — System health, processing metrics, failure alerts
- **Responsive Web UI** — Modern SaaS interface inspired by best-in-class design

---

## Architecture

```
                    ┌──────────────────┐
                    │   React Frontend │
                    │   (Antimetal UI) │
                    └────────┬─────────┘
                             │ HTTPS/WSS
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼─────────┐   │   ┌──────────▼──────────┐
    │   Document Upload │   │   │   LLM Chat Panel    │
    │   + OCR Capture   │   │   │   (Gemini Flash)    │
    └─────────┬─────────┘   │   └──────────┬──────────┘
              │              │              │
    ┌─────────▼──────────────▼──────────────▼──────────┐
    │              FastAPI Backend                      │
    │  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │
    │  │   Document   │  │  Healthcare  │  │ MLflow │ │
    │  │  Processor   │  │  LLM Service │  │ Tracker│ │
    │  └──────────────┘  └──────────────┘  └────────┘ │
    │  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │
    │  │   HIPAA      │  │   Keyword    │  │ Audit  │ │
    │  │  Security    │  │  Classifier  │  │ Logger │ │
    │  └──────────────┘  └──────────────┘  └────────┘ │
    └──────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌────────────────┐ ┌──────────┐ ┌──────────────┐
    │  MLflow Server │ │  SQLite  │ │  File Store  │
    │  (Tracking)    │ │  (Meta)  │ │  (Uploads)   │
    └────────────────┘ └──────────┘ └──────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- 4GB RAM minimum, 8GB recommended

### Run the Full Stack

```bash
git clone <repository-url>
cd claimscribe-ai

# Start all services (MLflow + Backend + Frontend)
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# MLflow UI: http://localhost:5000
```

---

## Deploy to Render.com (Free, Public URL)

The repo includes a `render.yaml` blueprint. One-click deploy:

1. Push this repo to GitHub.
2. On Render: **New → Blueprint → select this repo**. Render reads `render.yaml` and provisions both services.
3. On first deploy, set these dashboard env vars (blueprint marks them `sync: false`):
   - `GEMINI_API_KEY` on `claimscribe-backend` (optional; omit to use built-in mock responses — system still works)
   - `CORS_ORIGINS` on `claimscribe-backend` → set to your frontend URL, e.g. `https://claimscribe-frontend.onrender.com`
   - `VITE_API_URL` on `claimscribe-frontend` → set to your backend URL, e.g. `https://claimscribe-backend.onrender.com`
4. Redeploy both services after setting env vars. Your shareable URL is the frontend's `.onrender.com` URL.

**Free-tier caveats:**
- Backend spins down after 15 min idle; first request takes ~30s to wake.
- Ephemeral storage — uploaded documents and MLflow runs reset on redeploy. For persistence, add a Render Disk (paid) and mount it at `/app/data`.
- MLflow UI isn't exposed publicly on free tier. Access experiment data via `GET /api/v1/documents/metrics/classifier`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS + shadcn/ui |
| Backend | FastAPI + Python 3.11 |
| OCR | Tesseract OCR + pdfplumber + Pillow |
| LLM | Google Gemini 1.5 Flash (free tier) |
| ML Tracking | MLflow |
| Database | SQLite (metadata) |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Security | Fernet encryption, audit logging, PHI filtering |

---

## Project Structure

```
claimscribe-ai/
├── docker-compose.yml          # Full stack orchestration
├── README.md
├── .github/workflows/
│   └── ci-cd.yml               # GitHub Actions pipeline
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Configuration & secrets
│       ├── models/              # Pydantic schemas
│       ├── routers/             # API endpoints
│       ├── services/            # Business logic
│       │   ├── document_processor.py
│       │   ├── classifier.py
│       │   ├── llm_service.py
│       │   ├── ocr_service.py
│       │   └── mlflow_tracker.py
│       └── core/                # Security & compliance
│           ├── security.py
│           ├── audit_logger.py
│           └── encryption.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── Hero.tsx
        │   ├── UploadSection.tsx
        │   ├── Dashboard.tsx
        │   ├── LLMChat.tsx
        │   └── AnalyticsPanel.tsx
        └── hooks/useApi.ts
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload & process document |
| POST | `/api/v1/documents/capture` | Process camera-captured image |
| GET | `/api/v1/documents/` | List processed documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| GET | `/api/v1/documents/{id}/download` | Download as CSV/Excel |
| POST | `/api/v1/llm/query` | Healthcare LLM query |
| GET | `/api/v1/llm/conversations` | Chat history |
| GET | `/api/v1/health/status` | System health |
| GET | `/api/v1/monitoring/metrics` | Processing metrics |

---

## Security & HIPAA Considerations

- **Encryption at Rest**: All uploaded documents encrypted with Fernet (AES-128)
- **Audit Logging**: Every access, upload, and query is logged with timestamp & user
- **PHI Filtering**: Automatic detection and masking of sensitive health information
- **Secure Transmission**: HTTPS-only API communication
- **Data Retention**: Configurable automatic purging of processed documents
- **No External Data Leak**: All processing happens within containerized environment

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) includes:

1. **Lint & Test** — Python pytest + ESLint for frontend
2. **Security Scan** — Bandit for Python vulnerabilities
3. **Build & Push** — Docker image build and registry push
4. **Deploy** — Automated deployment to staging

---

## Model Versioning with MLflow

Every document processed and classified is tracked in MLflow:

- **Experiments**: Each classification run is logged
- **Metrics**: Accuracy, confidence score, processing time
- **Artifacts**: Classified documents, confusion matrices
- **Model Registry**: Trained classifier models versioned

Access MLflow UI at `http://localhost:5000` to view experiments.

---

## License

Proprietary — Built for case study demonstration purposes.
