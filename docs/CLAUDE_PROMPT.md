# ClaimScribe AI - Complete Claude Code Prompt

> **Copy and paste this entire prompt into Claude Code to reproduce the project.**

---

```
I need you to build a production-grade Healthcare Document Intelligence Platform called "ClaimScribe AI". This is for a job interview case study and must be extremely polished, robust, and deployable.

## PROJECT OVERVIEW
Build an end-to-end automated document ingestion and classification system for US health insurance claims processing. The system must:
- Ingest documents (PDFs, scanned images, camera captures, DOCX, TXT)
- Extract text using OCR (Tesseract) for scanned documents
- Classify claims into: inpatient, outpatient, pharmacy
- Provide a Healthcare domain LLM for document analysis (Gemini Flash)
- Store extracted data in structured DataFrame format with inferred columns
- Track everything in MLflow (model versioning, experiments, metrics)
- Implement HIPAA compliance (encryption, PHI detection, audit logging)
- Include CI/CD pipeline (GitHub Actions), Docker containerization
- Have a stunning web UI (React + Tailwind, inspired by antimetal.com)

## ARCHITECTURE
```
Frontend (React 18 + TypeScript + Tailwind) <-> FastAPI Backend (Python) <-> MLflow + SQLite + File Store
```

## TECH STACK
- Frontend: React 18, TypeScript, Tailwind CSS, Vite, Recharts, Framer Motion, react-dropzone, react-webcam
- Backend: FastAPI, Python 3.11, uvicorn
- OCR: pytesseract, pdfplumber, pdf2image, Pillow
- ML: scikit-learn, pandas, numpy, MLflow 2.12
- LLM: google-generativeai (Gemini 1.5 Flash free tier)
- Security: cryptography (Fernet AES-128), python-jose, passlib
- Container: Docker + Docker Compose
- CI/CD: GitHub Actions

## DIRECTORY STRUCTURE
```
claimscribe-ai/
├── docker-compose.yml              # Orchestrates all services
├── .env.example                    # Environment template
├── .dockerignore
├── .github/workflows/ci-cd.yml     # CI/CD pipeline
├── README.md                       # Full documentation
├── backend/
│   ├── Dockerfile                  # Python 3.11 + Tesseract
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app factory
│       ├── config.py               # Pydantic settings
│       ├── models/schemas.py       # All Pydantic models
│       ├── routers/
│       │   ├── documents.py        # Upload, list, export endpoints
│       │   ├── llm.py              # Healthcare LLM query endpoints
│       │   └── health.py           # Health checks + metrics
│       ├── services/
│       │   ├── document_processor.py  # Main orchestrator
│       │   ├── ocr_service.py         # Tesseract OCR pipeline
│       │   ├── classifier.py          # Keyword-based classification
│       │   ├── llm_service.py         # Gemini integration
│       │   └── mlflow_tracker.py      # MLflow wrapper
│       └── core/
│           ├── security.py         # Encryption + PHI detection
├── frontend/
│   ├── Dockerfile                  # Node 20 + Nginx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── components/
│       │   ├── Header.tsx
│       │   ├── Hero.tsx            # Centered hero with gradient
│       │   ├── UploadSection.tsx   # File dropzone + camera capture
│       │   ├── Dashboard.tsx       # Document list + detail panel
│       │   ├── LLMChat.tsx         # Healthcare AI chat interface
│       │   ├── AnalyticsPanel.tsx  # Charts + system health
│       │   └── Footer.tsx
│       └── types/
└── docs/
    ├── ARCHITECTURE.md
    └── DEPLOYMENT.md
```

## IMPLEMENTATION REQUIREMENTS

### Backend (FastAPI)
1. **main.py**: App factory with CORS, middleware (request timing), exception handlers, startup/shutdown events
2. **config.py**: Pydantic Settings with env var support, cached settings
3. **models/schemas.py**: DocumentType enum, all request/response models, ExportFormat enum
4. **services/ocr_service.py**: Extract from PDF (direct + OCR fallback), images, DOCX, TXT. Preprocess: grayscale, contrast, sharpness, denoise, resize
5. **services/classifier.py**: Weighted keyword scoring for inpatient/outpatient/pharmacy. Softmax normalization, ambiguity detection, confidence threshold, fallback classification. Log every classification to MLflow
6. **services/llm_service.py**: Google Gemini integration with healthcare system prompt, PHI masking before API calls, conversation memory, mock fallback when no API key. Suggested queries, structured responses
7. **services/document_processor.py**: Orchestrate: validate -> encrypt (Fernet) -> store -> OCR -> PHI detect -> classify -> structure data -> save. DataFrame export with inferred columns
8. **services/mlflow_tracker.py**: Log classifications, model training, system metrics. Get experiment summaries
9. **core/security.py**: Fernet encryption (PBKDF2 key derivation), PHI detector with regex patterns (SSN, phone, email, MRN, DOB, account), PHI masking, audit logger with hashed identifiers
10. **routers/documents.py**: POST /upload, POST /capture, GET /, GET /{id}, POST /export
11. **routers/llm.py**: POST /query, GET /conversations, GET /conversations/{id}
12. **routers/health.py**: GET /status, GET /metrics, GET /ready, GET /live

### Frontend (React + Tailwind)
1. **Design**: Clean SaaS aesthetic inspired by antimetal.com. Soft gradients (blue/green tones), rounded corners, subtle shadows, generous whitespace
2. **Hero**: Centered layout, gradient text, feature pills with icons, fade-in animations
3. **UploadSection**: Toggle between file upload (drag-drop zone with react-dropzone) and camera capture (react-webcam). Show classification result with confidence bar, metrics, text preview
4. **Dashboard**: Split panel - document list on left (with type badges, confidence %), detail panel on right (structured data, inferred columns, MLflow link, text preview)
5. **LLMChat**: Chat interface with suggested queries, message history, typing indicator, healthcare avatar, PHI-safe badge
6. **AnalyticsPanel**: 4 stat cards, 3 charts (Pie for type distribution, Bar for confidence, Area for volume trend), activity log, system health panel with MLflow link
7. **Header**: Sticky with blur backdrop, logo, system status, links to MLflow and API docs
8. **Footer**: 3-column layout with brand, platform links, tech stack

### Docker
- **docker-compose.yml**: MLflow (port 5000), Backend (port 8000), Frontend (port 5173). Shared network, volumes for persistence
- **Backend Dockerfile**: Python 3.11-slim, install Tesseract + image libs, pip install, uvicorn
- **Frontend Dockerfile**: Multi-stage (Node build + Nginx serve), SPA routing config

### CI/CD (.github/workflows/ci-cd.yml)
- Test backend: flake8 lint, bandit security scan, pytest
- Test frontend: npm lint, TypeScript check, build
- Build and push Docker images to GHCR
- Optional Azure deploy step

### MLflow Integration
- Every classification logged as a run with params (doc_id, predicted_type) and metrics (confidence, processing_time, per-type scores)
- Experiment tracking with summaries
- Model registry for trained classifiers
- Access at http://localhost:5000

### Security & HIPAA
- AES-128 encryption at rest (Fernet)
- PHI detection and automatic masking
- Audit logging of all events
- Secure headers, CORS protection
- No PHI in LLM API calls (filtered before sending)

## KEYWORDS FOR CLASSIFICATION
```python
INPATIENT: inpatient, hospital admission, admitted, hospital stay, overnight, room and board, inpatient care, hospitalization, icu, intensive care, surgical suite, operating room, recovery room, length of stay, discharge summary, admitting diagnosis, principal diagnosis, attending physician, hospitalist, bed day, inpatient facility, acute care, snf, rehabilitation facility

OUTPATIENT: outpatient, office visit, clinic, ambulatory, urgent care, emergency room, er visit, same day, day surgery, procedure room, consultation, follow-up, follow up, annual physical, preventive care, diagnostic test, laboratory, imaging, x-ray, mri, ct scan, ultrasound, walk-in, outpatient surgery, outpatient procedure, outpatient clinic, outpatient department, opd

PHARMACY: pharmacy, prescription, rx, medication, drug, pharmaceutical, dispense, dispensing, ndc, drug code, generic, brand name, dosage, quantity, days supply, refill, prior authorization, prior auth, formulary, therapeutic, pharmacist, mail order, specialty pharmacy, compound, unit price, ingredient cost, dispensing fee, awp, wac
```

## ENVIRONMENT VARIABLES
```
SECRET_KEY, ENCRYPTION_KEY, GEMINI_API_KEY, MLFLOW_TRACKING_URI,
ENVIRONMENT, DEBUG, CORS_ORIGINS, DATABASE_URL, VITE_API_URL
```

## RUNNING THE PROJECT
```bash
docker-compose up --build
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# MLflow UI: http://localhost:5000
```

## DELIVERABLES
1. All source code files as specified
2. Working Docker Compose setup
3. CI/CD pipeline
4. README with architecture diagrams
5. Environment template

Build this entire project now. Make sure the code is production-quality, error-free, and elegantly designed. The UI should be stunning and impress interviewers.
```

---

## How to Use This Prompt

1. **Open Claude Code** in your project directory
2. **Paste the entire prompt above** (between the triple backticks)
3. **Review the generated files** as Claude creates them
4. **Run** `docker-compose up --build` to start everything
5. **Access** the application at the URLs listed above

## Tips for the Interview

- **Show the MLflow UI** - it demonstrates professional ML ops
- **Upload a sample document** - show the full pipeline working
- **Ask the LLM questions** - demonstrate domain expertise
- **Point out the security features** - HIPAA compliance is critical
- **Explain the CI/CD pipeline** - shows production readiness
- **Discuss scalability** - Docker Compose -> Kubernetes path
