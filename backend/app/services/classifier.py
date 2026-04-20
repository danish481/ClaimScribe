"""
ClaimScribe AI - Document Classifier
Keyword-based classification engine for health insurance claims
with confidence scoring and MLflow tracking
"""

import re
import time
import uuid
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import mlflow
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib

from app.config import settings
from app.models.schemas import DocumentType, ClassifierMetrics
from app.core.security import AuditLogger


# ── Classification Keywords ───────────────────────────────

CLAIM_KEYWORDS = {
    DocumentType.INPATIENT: {
        # High-weight keywords
        "inpatient": 5.0,
        "hospital admission": 5.0,
        "admitted": 4.0,
        "hospital stay": 4.0,
        "overnight": 3.0,
        "room and board": 3.0,
        "inpatient care": 5.0,
        "hospitalization": 4.0,
        "icu": 3.5,
        "intensive care": 3.5,
        "surgical suite": 3.0,
        "operating room": 3.0,
        "recovery room": 2.5,
        "length of stay": 2.5,
        "discharge summary": 2.5,
        "admitting diagnosis": 3.0,
        "principal diagnosis": 2.5,
        "attending physician": 2.0,
        "hospitalist": 3.0,
        "bed day": 2.5,
        "inpatient facility": 4.0,
        "acute care": 2.5,
        "snf": 2.0,  # Skilled nursing facility
        "rehabilitation facility": 2.0,
    },
    DocumentType.OUTPATIENT: {
        # High-weight keywords
        "outpatient": 5.0,
        "office visit": 4.0,
        "clinic": 3.0,
        "ambulatory": 3.5,
        "urgent care": 3.5,
        "emergency room": 3.5,
        "er visit": 3.5,
        "same day": 2.5,
        "day surgery": 3.0,
        "procedure room": 2.5,
        "consultation": 2.0,
        "follow-up": 2.0,
        "follow up": 2.0,
        "annual physical": 2.5,
        "preventive care": 2.0,
        "diagnostic test": 2.0,
        "laboratory": 1.5,
        "imaging": 1.5,
        "x-ray": 1.5,
        "mri": 1.5,
        "ct scan": 1.5,
        "ultrasound": 1.5,
        "walk-in": 2.0,
        "outpatient surgery": 4.0,
        "outpatient procedure": 4.0,
        "outpatient clinic": 3.5,
        "outpatient department": 3.5,
        "opd": 3.0,
    },
    DocumentType.PHARMACY: {
        # High-weight keywords
        "pharmacy": 5.0,
        "prescription": 5.0,
        "rx": 4.0,
        "medication": 4.0,
        "drug": 3.5,
        "pharmaceutical": 3.5,
        "dispense": 3.5,
        "dispensing": 3.0,
        "ndc": 3.5,  # National Drug Code
        "drug code": 3.0,
        "generic": 2.0,
        "brand name": 2.0,
        "dosage": 2.5,
        "quantity": 1.5,
        "days supply": 3.0,
        "refill": 3.0,
        "prior authorization": 2.5,
        "prior auth": 2.5,
        "formulary": 3.0,
        "therapeutic": 2.0,
        "pharmacist": 2.5,
        "mail order": 2.5,
        "specialty pharmacy": 4.0,
        "compound": 2.0,
        "unit price": 1.5,
        "ingredient cost": 2.5,
        "dispensing fee": 2.5,
        "awp": 2.0,  # Average Wholesale Price
        "wac": 2.0,  # Wholesale Acquisition Cost
    },
}

# Ambiguity patterns - reduce confidence when these co-occur
AMBIGUITY_PATTERNS = [
    (DocumentType.INPATIENT, DocumentType.OUTPATIENT, ["surgery", "procedure"]),
    (DocumentType.INPATIENT, DocumentType.PHARMACY, ["medication", "drug", "prescription"]),
    (DocumentType.OUTPATIENT, DocumentType.PHARMACY, ["treatment", "therapy"]),
]


class DocumentClassifier:
    """
    Healthcare claims document classifier.

    Uses a hybrid approach:
    1. Keyword-based scoring with weighted terms
    2. Confidence calculation with ambiguity detection
    3. MLflow tracking for all classifications
    """

    def __init__(self):
        self.keywords = CLAIM_KEYWORDS
        self.confidence_threshold = settings.CLASSIFICATION_CONFIDENCE_THRESHOLD
        self._mlflow_initialized = False
        self._ml_model = None

    def _init_mlflow(self):
        """Initialize MLflow tracking."""
        if not self._mlflow_initialized:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
            self._mlflow_initialized = True

    def classify(self, text: str, document_id: Optional[str] = None) -> Dict:
        """
        Classify extracted text into claim type.

        Returns dict with:
            - predicted_type: DocumentType
            - confidence: float (0-1)
            - scores: dict of scores per type
            - method: str (keyword_based)
            - mlflow_run_id: str
        """
        start_time = time.time()
        self._init_mlflow()

        # Preprocess text
        processed_text = self._preprocess_text(text)

        # Calculate scores for each category
        scores = self._calculate_scores(processed_text)

        # Determine predicted type
        predicted_type, confidence = self._determine_type(scores, processed_text)

        # Check for ambiguity
        is_ambiguous = self._check_ambiguity(scores, processed_text)
        if is_ambiguous:
            confidence *= 0.7  # Reduce confidence for ambiguous cases

        # Log to MLflow
        processing_time = (time.time() - start_time) * 1000
        mlflow_run_id = self._log_classification(
            text=processed_text[:1000],
            document_id=document_id,
            predicted_type=predicted_type.value,
            confidence=confidence,
            scores=scores,
            processing_time=processing_time,
            is_ambiguous=is_ambiguous,
        )

        # Audit log
        AuditLogger.log_event(
            event_type="document_classified",
            resource_type="document",
            resource_id=document_id or str(uuid.uuid4()),
            details={
                "predicted_type": predicted_type.value,
                "confidence": confidence,
                "is_ambiguous": is_ambiguous,
            }
        )

        return {
            "predicted_type": predicted_type,
            "confidence": round(confidence, 4),
            "scores": {k.value: round(v, 4) for k, v in scores.items()},
            "method": "keyword_based_v2",
            "mlflow_run_id": mlflow_run_id,
            "is_ambiguous": is_ambiguous,
            "processing_time_ms": round(processing_time, 2),
        }

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for classification."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep medical punctuation
        text = re.sub(r'[^\w\s/\-().,:;]', ' ', text)
        return text.strip()

    def _calculate_scores(self, text: str) -> Dict[DocumentType, float]:
        """Calculate weighted keyword scores for each document type."""
        scores = {doc_type: 0.0 for doc_type in DocumentType if doc_type != DocumentType.UNKNOWN}

        for doc_type, keywords in self.keywords.items():
            for keyword, weight in keywords.items():
                # Count occurrences
                count = text.count(keyword)
                if count > 0:
                    # Apply weight with diminishing returns for repeated keywords
                    score_contribution = weight * min(count, 3)  # Cap at 3 occurrences
                    scores[doc_type] += score_contribution

        # Normalize scores to 0-1 range using softmax-like normalization
        return self._normalize_scores(scores)

    def _normalize_scores(self, scores: Dict[DocumentType, float]) -> Dict[DocumentType, float]:
        """Normalize scores so they sum to 1 (probability-like)."""
        total = sum(scores.values())
        if total == 0:
            return {k: 0.0 for k in scores}

        # Softmax normalization
        import math
        exp_scores = {k: math.exp(v) for k, v in scores.items()}
        total_exp = sum(exp_scores.values())
        return {k: v / total_exp for k, v in exp_scores.items()}

    def _determine_type(
        self,
        scores: Dict[DocumentType, float],
        text: str
    ) -> Tuple[DocumentType, float]:
        """Determine document type from normalized scores."""
        # Filter out UNKNOWN
        valid_scores = {k: v for k, v in scores.items() if k != DocumentType.UNKNOWN}

        if not valid_scores or max(valid_scores.values()) == 0:
            # Fallback: try to infer from context
            return self._fallback_classification(text)

        predicted = max(valid_scores, key=valid_scores.get)
        confidence = valid_scores[predicted]

        # Apply confidence threshold
        if confidence < self.confidence_threshold:
            return DocumentType.UNKNOWN, confidence

        return predicted, confidence

    def _fallback_classification(self, text: str) -> Tuple[DocumentType, float]:
        """Fallback classification when no keywords match."""
        # Check for common medical terms that might indicate type
        pharmacy_indicators = ["mg", "tablet", "capsule", "injection", "iv", "oral"]
        inpatient_indicators = ["admission date", "discharge date", "hospital"]

        text_lower = text.lower()
        pharm_score = sum(1 for ind in pharmacy_indicators if ind in text_lower)
        inpatient_score = sum(1 for ind in inpatient_indicators if ind in text_lower)

        if pharm_score > inpatient_score and pharm_score > 0:
            return DocumentType.PHARMACY, 0.4
        elif inpatient_score > 0:
            return DocumentType.INPATIENT, 0.4

        return DocumentType.UNKNOWN, 0.0

    def _check_ambiguity(self, scores: Dict[DocumentType, float], text: str) -> bool:
        """Check if document is ambiguous (multiple high scores)."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_scores) < 2:
            return False

        top_score = sorted_scores[0][1]
        second_score = sorted_scores[1][1]

        # If top two scores are close (within 20%), consider ambiguous
        if second_score > 0 and (top_score - second_score) / second_score < 0.2:
            return True

        return False

    def _log_classification(
        self,
        text: str,
        document_id: Optional[str],
        predicted_type: str,
        confidence: float,
        scores: Dict,
        processing_time: float,
        is_ambiguous: bool,
    ) -> str:
        """Log classification run to MLflow."""
        try:
            with mlflow.start_run(run_name=f"classify_{document_id or 'unknown'}") as run:
                # Log parameters
                mlflow.log_param("document_id", document_id or "unknown")
                mlflow.log_param("predicted_type", predicted_type)
                mlflow.log_param("is_ambiguous", is_ambiguous)
                mlflow.log_param("text_length", len(text))

                # Log metrics
                mlflow.log_metric("confidence", confidence)
                mlflow.log_metric("processing_time_ms", processing_time)

                for doc_type, score in scores.items():
                    mlflow.log_metric(f"score_{doc_type.value}", score)

                # Log text sample as artifact
                sample_path = f"/tmp/sample_{run.info.run_id}.txt"
                with open(sample_path, 'w') as f:
                    f.write(text[:2000])
                mlflow.log_artifact(sample_path, "text_samples")

                return run.info.run_id

        except Exception as e:
            print(f"MLflow logging error: {e}")
            return ""

    def batch_classify(self, texts: List[str]) -> List[Dict]:
        """Classify multiple documents."""
        results = []
        for i, text in enumerate(texts):
            result = self.classify(text, document_id=f"batch_{i}")
            results.append(result)
        return results

    def train_ml_model(self, texts: List[str], labels: List[str]) -> ClassifierMetrics:
        """
        Train a machine learning classifier on labeled data.
        Logs model and metrics to MLflow.
        """
        self._init_mlflow()

        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        # Create pipeline
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('classifier', MultinomialNB()),
        ])

        with mlflow.start_run(run_name="classifier_training") as run:
            # Train
            pipeline.fit(X_train, y_train)

            # Predict
            y_pred = pipeline.predict(X_test)

            # Metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average=None, labels=['inpatient', 'outpatient', 'pharmacy']
            )
            cm = confusion_matrix(y_test, y_pred, labels=['inpatient', 'outpatient', 'pharmacy'])

            # Log metrics
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_param("training_samples", len(X_train))
            mlflow.log_param("test_samples", len(X_test))

            # Log model
            mlflow.sklearn.log_model(pipeline, "classifier_model")

            metrics = ClassifierMetrics(
                accuracy=accuracy,
                precision={
                    'inpatient': precision[0],
                    'outpatient': precision[1],
                    'pharmacy': precision[2],
                },
                recall={
                    'inpatient': recall[0],
                    'outpatient': recall[1],
                    'pharmacy': recall[2],
                },
                f1_score={
                    'inpatient': f1[0],
                    'outpatient': f1[1],
                    'pharmacy': f1[2],
                },
                confusion_matrix=cm.tolist(),
                training_samples=len(X_train),
                test_samples=len(X_test),
                mlflow_run_id=run.info.run_id,
            )

            self._ml_model = pipeline
            return metrics


# ── Singleton ─────────────────────────────────────────────
classifier = DocumentClassifier()
