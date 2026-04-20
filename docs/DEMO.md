# ClaimScribe AI — Demo & Interview Guide

## 3-Minute Demo Script

This script covers the four things that matter most to a technical interviewer: document intelligence, LLM integration, API documentation, and ML tracking.

**(1) Upload a sample claims PDF.** Open the frontend, drag `backend/tests/samples/sample_pharmacy_claim.txt` onto the upload zone, and click Process. Within a second or two the dashboard shows `detected_type: pharmacy`, `confidence: ~0.92`, and a preview of the extracted text. Point out that the file was encrypted before OCR ran — the raw bytes on disk are Fernet ciphertext.

**(2) Ask the LLM a question.** Switch to the LLM Chat panel and type: "What type of claim is this and what is the NDC code?" The assistant responds citing the uploaded document. If `GEMINI_API_KEY` is not set, the mock path fires and still returns a structured healthcare response — the system degrades gracefully. Either way, note that the prompt went through `PHIDetector.mask_phi()` before leaving the backend, so the Gemini API never saw the raw text.

**(3) Open /docs.** Navigate to `{backend_url}/docs`. Show the interactive OpenAPI UI: every endpoint is documented with request schemas, response models, and example values. Pick `POST /api/v1/documents/upload`, click Try It Out, and upload the pharmacy sample directly from the API. This demonstrates that the backend is accessible independently of the frontend — useful for integrations.

**(4) Show MLflow.** When running locally with `docker-compose up`, open `http://localhost:5000`. Click the `claimscribe-document-classification` experiment, then the latest run. Show `confidence`, `processing_time_ms`, and `score_pharmacy` metrics, plus the text artifact logged under `text_samples/`. On Render (no separate MLflow service) the same data is available via `GET /api/v1/documents/metrics/classifier`.

---

## Five Likely Interview Questions

**"How do you handle ambiguous documents where multiple claim types are plausible?"**
Look at `classifier._check_ambiguity()` ([backend/app/services/classifier.py](../backend/app/services/classifier.py), line ~291). After softmax normalization, if the second-highest score is within 20% of the top score, the document is flagged as ambiguous and `confidence` is multiplied by 0.7. The `is_ambiguous` flag propagates into `structured_data` so downstream analytics can filter these for human review. The penalty is intentional — it's better to surface uncertainty than to overstate confidence on a billing document.

**"What stops PHI from leaking to the Gemini API?"**
`PHIDetector.mask_phi()` in `app/core/security.py` (line ~89) runs regex substitutions for SSNs, phone numbers, emails, MRNs, and dates of birth before the text is inserted into the LLM prompt. The masking is applied in `llm_service._build_context()`. On the upload path, the original text is stored encrypted and only the masked version is used for external calls.

**"Why keyword-based classification instead of a fine-tuned transformer?"**
No labeled training data exists at bootstrap time. A BERT-class model trained on zero examples would just guess. The keyword approach is deterministic, interpretable, immediately useful, and easy to audit under HIPAA. `classifier.train_ml_model()` exists to absorb labeled data as it accumulates and log the resulting sklearn pipeline to MLflow. The architecture supports an A/B switch between keyword and ML predictions once the ML model's accuracy on a held-out validation set exceeds the keyword baseline.

**"How does the export download work? Isn't the download URL a security risk?"**
The `export_dataframe()` method in `document_processor.py` stores a mapping of `export_id → file_path` and `export_id → expires_at` in memory. The download endpoint looks up the path, checks expiry (default 24 hours via `EXPORT_LINK_TTL_HOURS`), and streams the file. The ID is a UUID4, so brute-forcing is not feasible. In production, the next step would be signed URLs (AWS S3 presigned, Azure SAS tokens) with server-side HMAC verification.

**"What happens when Gemini is rate-limited or unavailable?"**
`llm_service.query()` catches all exceptions from the `google.generativeai` client and falls back to `_generate_mock_response()`, which returns a plausible structured healthcare response. The fallback is also triggered automatically when `GEMINI_API_KEY` is not set. The mock is intentionally realistic enough that a demo works without any API key. This is surfaced in `/api/v1/health/status` as `"status": "degraded", "message": "Using mock responses"`.

---

## Known Limitations

**Free-tier cold starts (~30 seconds).** Render spins down the backend container after 15 minutes of inactivity. The first request after idle wakes the container; users will see a timeout or slow response. Upgrading to a paid Render plan eliminates this.

**Ephemeral storage resets on redeploy.** All uploaded documents, MLflow runs, and the SQLite database live in `/app/data`, which is wiped whenever Render rebuilds the container. Adding a Render Disk ($7/month, mounted at `/app/data`) makes this persistent.

**Gemini free tier rate limit (~15 requests/minute).** The Gemini 1.5 Flash free tier enforces a rate limit that a demo with multiple concurrent users can easily hit. The mock fallback prevents errors, but responses will be less relevant. Using a paid Gemini API key or caching frequent queries would address this.

**In-memory document store.** `DocumentStore` is a Python dict. It does not survive restarts, does not scale across multiple workers, and has no query capability. Replacing it with SQLAlchemy + Postgres is the first production upgrade.
