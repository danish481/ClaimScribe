"""
ClaimScribe AI - MLflow Tracking Service
Comprehensive experiment tracking, model versioning, and metrics monitoring
"""

import os
import time
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from app.config import settings


class MLflowTracker:
    """
    Centralized MLflow tracking for all ML operations.

    Tracks:
    - Document classifications
    - Model training runs
    - System performance metrics
    - Data drift indicators
    """

    def __init__(self):
        self.tracking_uri = settings.MLFLOW_TRACKING_URI
        self.experiment_name = settings.MLFLOW_EXPERIMENT_NAME
        self._initialized = False

    def init(self):
        """Initialize MLflow connection."""
        if not self._initialized:
            try:
                mlflow.set_tracking_uri(self.tracking_uri)
                mlflow.set_experiment(self.experiment_name)
            except Exception as e:
                print(f"MLflow init warning: {e}")
            finally:
                self._initialized = True  # don't retry on every call

    def log_classification(
        self,
        document_id: str,
        text_sample: str,
        predicted_type: str,
        confidence: float,
        scores: Dict[str, float],
        processing_time_ms: float,
        is_ambiguous: bool = False,
    ) -> str:
        """Log a single document classification to MLflow."""
        self.init()

        with mlflow.start_run(run_name=f"doc_{document_id}") as run:
            # Parameters
            mlflow.log_param("document_id", document_id)
            mlflow.log_param("predicted_type", predicted_type)
            mlflow.log_param("is_ambiguous", is_ambiguous)
            mlflow.log_param("text_length", len(text_sample))

            # Metrics
            mlflow.log_metric("confidence", confidence)
            mlflow.log_metric("processing_time_ms", processing_time_ms)

            for doc_type, score in scores.items():
                mlflow.log_metric(f"score_{doc_type}", score)

            # Artifact: text sample
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="claimscribe_")
            try:
                with os.fdopen(tmp_fd, 'w') as f:
                    f.write(text_sample[:5000])
                mlflow.log_artifact(tmp_path, "text_samples")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            return run.info.run_id

    def log_model_training(
        self,
        model: Any,
        model_name: str,
        metrics: Dict[str, float],
        params: Dict[str, Any],
        test_data: Optional[pd.DataFrame] = None,
    ) -> str:
        """Log model training run with metrics and artifacts."""
        self.init()

        with mlflow.start_run(run_name=f"train_{model_name}") as run:
            # Log parameters
            for key, value in params.items():
                mlflow.log_param(key, value)

            # Log metrics
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)

            # Log model
            mlflow.sklearn.log_model(model, model_name)

            # Log test data sample if provided
            if test_data is not None:
                tmp_fd2, tmp_csv = tempfile.mkstemp(suffix=".csv", prefix="claimscribe_")
                try:
                    with os.fdopen(tmp_fd2, 'w') as f:
                        test_data.head(100).to_csv(f, index=False)
                    mlflow.log_artifact(tmp_csv, "test_data_sample")
                finally:
                    try:
                        os.unlink(tmp_csv)
                    except OSError:
                        pass

            return run.info.run_id

    def log_system_metrics(self, metrics: Dict[str, Any]):
        """Log system-level metrics (called periodically)."""
        self.init()

        with mlflow.start_run(run_name=f"system_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"):
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)

    def get_experiment_summary(self) -> Dict:
        """Get summary of experiment runs."""
        self.init()

        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        if not experiment:
            return {"error": "Experiment not found"}

        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=100,
        )

        if runs.empty:
            return {"total_runs": 0, "recent_runs": []}

        # Calculate aggregate metrics
        summary = {
            "total_runs": len(runs),
            "experiment_id": experiment.experiment_id,
            "experiment_name": experiment.name,
            "recent_runs": [],
        }

        # Recent runs summary
        for _, run in runs.head(10).iterrows():
            summary["recent_runs"].append({
                "run_id": run.run_id,
                "run_name": run.get("tags.mlflow.runName", "unnamed"),
                "status": run.status,
                "start_time": run.start_time.isoformat() if hasattr(run.start_time, 'isoformat') else str(run.start_time),
                "metrics": {k: v for k, v in run.items() if k.startswith("metrics.") and pd.notna(v)},
            })

        # Aggregate classification metrics
        if "metrics.confidence" in runs.columns:
            summary["avg_confidence"] = runs["metrics.confidence"].mean()
            summary["min_confidence"] = runs["metrics.confidence"].min()
            summary["max_confidence"] = runs["metrics.confidence"].max()

        if "metrics.processing_time_ms" in runs.columns:
            summary["avg_processing_time_ms"] = runs["metrics.processing_time_ms"].mean()

        return summary

    def compare_runs(self, run_ids: List[str]) -> pd.DataFrame:
        """Compare multiple runs side by side."""
        self.init()

        runs_data = []
        for run_id in run_ids:
            run = mlflow.get_run(run_id)
            runs_data.append({
                "run_id": run_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                **{f"param_{k}": v for k, v in run.data.params.items()},
                **{f"metric_{k}": v for k, v in run.data.metrics.items()},
            })

        return pd.DataFrame(runs_data)


# ── Singleton ─────────────────────────────────────────────
mlflow_tracker = MLflowTracker()
