# ClaimScribe AI - Deployment Guide

## Prerequisites

- Docker Engine 24.0+ & Docker Compose v2+
- Git
- 8GB RAM (4GB minimum)
- (Optional) Google Gemini API key (free tier)

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd claimscribe-ai

# 2. Set environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (optional)

# 3. Start all services
docker-compose up --build

# 4. Access the services
# Web App:     http://localhost:5173
# API Docs:    http://localhost:8000/docs
# MLflow UI:   http://localhost:5000
```

## Service Architecture

```
Host Machine
├── Port 5173 → Frontend (React + Nginx)
├── Port 8000 → Backend (FastAPI + Uvicorn)
└── Port 5000 → MLflow Tracking Server

Internal Network: claimscribe-network
├── backend → FastAPI
├── frontend → Nginx
└── mlflow → MLflow Server

Volumes:
├── mlflow_data → MLflow DB + Artifacts
└── backend_data → SQLite DB + Uploads
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | No | - | Google Gemini API key for LLM |
| `SECRET_KEY` | Yes | auto-generated | App secret key |
| `ENCRYPTION_KEY` | Yes | derived | Fernet encryption key |
| `ENVIRONMENT` | No | development | dev/staging/production |
| `MLFLOW_TRACKING_URI` | No | http://mlflow:5000 | MLflow server URL |

## Production Deployment

### Azure Container Instances

```bash
# Build images
docker-compose build

# Tag for ACR
docker tag claimscribe-backend <acr-name>.azurecr.io/claimscribe-backend:latest
docker tag claimscribe-frontend <acr-name>.azurecr.io/claimscribe-frontend:latest

# Push to ACR
docker push <acr-name>.azurecr.io/claimscribe-backend:latest
docker push <acr-name>.azurecr.io/claimscribe-frontend:latest

# Deploy via Azure CLI
az container create \
  --resource-group myResourceGroup \
  --file azure-deploy.yaml
```

### Kubernetes

```bash
# Generate manifests
kubectl apply -f k8s/

# Or use Helm
helm install claimscribe ./helm/
```

## Monitoring

- **Health Check**: `GET http://localhost:8000/api/v1/health/status`
- **Metrics**: `GET http://localhost:8000/api/v1/monitoring/metrics`
- **MLflow**: `http://localhost:5000`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change ports in `docker-compose.yml` |
| Tesseract not found | Ensure `tesseract-ocr` is installed in backend container |
| MLflow connection error | Check `MLFLOW_TRACKING_URI` env var |
| CORS errors | Verify `CORS_ORIGINS` includes your frontend URL |

## Backup & Recovery

```bash
# Backup volumes
docker run --rm -v claimscribe-ai_mlflow_data:/data -v $(pwd):/backup alpine tar czf /backup/mlflow-backup.tar.gz -C /data .
docker run --rm -v claimscribe-ai_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backend-backup.tar.gz -C /data .
```
