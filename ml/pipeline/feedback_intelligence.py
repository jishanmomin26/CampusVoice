"""Unified Feedback Intelligence Pipeline for CampusVoice.

Integrates:
  - Step 3: NLP Preprocessing with Negation Preservation
  - Step 4: Fitted TF-IDF Vectorizer (reused strictly without refitting)
  - Step 5: Baseline Sentiment Classification Model
  - Step 6: Baseline Category Classification Model

Provides in-memory caching of serialized models to avoid per-inference disk I/O.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

# Ensure project root and backend are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from app.nlp.preprocessing import preprocess_text

MODELS_DIR = ML_DIR / "models"

LABEL_TO_SENTIMENT: Dict[int, str] = {
    -1: "negative",
    0: "neutral",
    1: "positive",
}

CANONICAL_CATEGORIES = [
    "Teaching",
    "Course Content",
    "Examination",
    "Lab Work",
    "Library Facilities",
    "Extracurricular",
]

ALLOWED_MODEL_NAMES = {"best", "logistic_regression", "naive_bayes"}


def _resolve_model_type_name(model_obj: Any) -> str:
    """Returns human-readable model type name."""
    if isinstance(model_obj, LogisticRegression):
        return "logistic_regression"
    if isinstance(model_obj, MultinomialNB):
        return "naive_bayes"
    return type(model_obj).__name__.lower()


class FeedbackIntelligencePipeline:
    """In-memory inference pipeline for student feedback intelligence.

    Loads the TF-IDF vectorizer, sentiment model, and category model once
    upon initialization and caches them in memory for fast repeated inference.
    """

    def __init__(
        self,
        sentiment_model: str = "best",
        category_model: str = "best",
        models_dir: Optional[Path] = None,
    ) -> None:
        """Initializes pipeline and loads serialized models into memory.

        Args:
            sentiment_model: One of 'best', 'logistic_regression', 'naive_bayes'.
            category_model: One of 'best', 'logistic_regression', 'naive_bayes'.
            models_dir: Custom directory containing model artifacts.

        Raises:
            ValueError: If an invalid model name is requested.
            FileNotFoundError: If a required model or vectorizer artifact is missing.
        """
        self.sentiment_model_option = sentiment_model.lower().strip()
        self.category_model_option = category_model.lower().strip()
        self.models_dir = Path(models_dir) if models_dir else MODELS_DIR

        # Validate requested options
        if self.sentiment_model_option not in ALLOWED_MODEL_NAMES:
            raise ValueError(
                f"Invalid sentiment model '{sentiment_model}'. "
                f"Choose from: {sorted(ALLOWED_MODEL_NAMES)}"
            )
        if self.category_model_option not in ALLOWED_MODEL_NAMES:
            raise ValueError(
                f"Invalid category model '{category_model}'. "
                f"Choose from: {sorted(ALLOWED_MODEL_NAMES)}"
            )

        # 1. Load Step 4 TF-IDF Vectorizer
        vectorizer_path = self.models_dir / "tfidf_vectorizer.joblib"
        if not vectorizer_path.exists():
            raise FileNotFoundError(
                f"TF-IDF vectorizer artifact not found at: {vectorizer_path}. "
                "Step 4 feature engineering pipeline must be executed first."
            )
        self._vectorizer = joblib.load(vectorizer_path)

        # 2. Load Sentiment Model
        sentiment_filename_map = {
            "best": "best_sentiment_model.joblib",
            "logistic_regression": "logistic_regression_sentiment.joblib",
            "naive_bayes": "naive_bayes_sentiment.joblib",
        }
        sentiment_path = self.models_dir / sentiment_filename_map[self.sentiment_model_option]
        if not sentiment_path.exists():
            raise FileNotFoundError(
                f"Sentiment model artifact not found at: {sentiment_path}. "
                "Step 5 model training pipeline must be executed first."
            )
        self._sentiment_model = joblib.load(sentiment_path)
        self._sentiment_model_name = _resolve_model_type_name(self._sentiment_model)

        # 3. Load Category Model
        category_filename_map = {
            "best": "best_category_model.joblib",
            "logistic_regression": "logistic_regression_category.joblib",
            "naive_bayes": "naive_bayes_category.joblib",
        }
        category_path = self.models_dir / category_filename_map[self.category_model_option]
        if not category_path.exists():
            raise FileNotFoundError(
                f"Category model artifact not found at: {category_path}. "
                "Step 6 model training pipeline must be executed first."
            )
        self._category_model = joblib.load(category_path)
        self._category_model_name = _resolve_model_type_name(self._category_model)

    def analyze_feedback(self, text: str) -> Dict[str, Any]:
        """Analyzes raw student feedback text through the unified pipeline.

        Args:
            text: Raw student feedback string.

        Returns:
            Dict[str, Any]: Unified feedback intelligence result matching contract.

        Raises:
            ValueError: If input is None, empty, or whitespace-only.
            TypeError: If input is not a string.
        """
        # Input validation
        if text is None:
            raise ValueError("Input feedback text cannot be None.")
        if not isinstance(text, str):
            raise TypeError(f"Input feedback text must be a string, got {type(text).__name__}.")
        if not text.strip():
            raise ValueError("Input feedback text cannot be empty or whitespace-only.")

        # Step 3 NLP Preprocessing (preserves negation)
        prep_result = preprocess_text(text)
        clean_text = prep_result.clean_text

        # TF-IDF Feature Transformation (transform only, strictly never fit)
        X_vec = self._vectorizer.transform([clean_text])

        # --- Sentiment Classification ---
        sentiment_label = int(self._sentiment_model.predict(X_vec)[0])
        sentiment_name = LABEL_TO_SENTIMENT.get(sentiment_label, "unknown")

        sentiment_probs: Optional[Dict[str, float]] = None
        sentiment_conf = 1.0
        if hasattr(self._sentiment_model, "predict_proba"):
            s_probs = self._sentiment_model.predict_proba(X_vec)[0]
            s_classes = self._sentiment_model.classes_
            sentiment_probs = {
                LABEL_TO_SENTIMENT.get(int(cls), str(cls)): float(prob)
                for cls, prob in zip(s_classes, s_probs)
            }
            sentiment_conf = float(max(s_probs))

        # --- Category Classification ---
        category_name = str(self._category_model.predict(X_vec)[0])

        category_probs: Optional[Dict[str, float]] = None
        category_conf = 1.0
        if hasattr(self._category_model, "predict_proba"):
            c_probs = self._category_model.predict_proba(X_vec)[0]
            c_classes = self._category_model.classes_
            category_probs = {
                str(cls): float(prob)
                for cls, prob in zip(c_classes, c_probs)
            }
            category_conf = float(max(c_probs))

        return {
            "feedback": text,
            "clean_text": clean_text,
            "sentiment": {
                "label": sentiment_label,
                "name": sentiment_name,
                "confidence": sentiment_conf,
                "probabilities": sentiment_probs,
            },
            "category": {
                "name": category_name,
                "confidence": category_conf,
                "probabilities": category_probs,
            },
            "models": {
                "sentiment": self._sentiment_model_name,
                "category": self._category_model_name,
            },
        }


# Global singleton instance for module-level convenience function
_cached_pipeline: Optional[FeedbackIntelligencePipeline] = None


def analyze_feedback(
    text: str,
    sentiment_model: str = "best",
    category_model: str = "best",
) -> Dict[str, Any]:
    """Convenience function to analyze student feedback using a cached pipeline instance.

    Reuses in-memory loaded pipeline instance to avoid reloading models from disk.
    """
    global _cached_pipeline
    if (
        _cached_pipeline is None
        or _cached_pipeline.sentiment_model_option != sentiment_model.lower().strip()
        or _cached_pipeline.category_model_option != category_model.lower().strip()
    ):
        _cached_pipeline = FeedbackIntelligencePipeline(
            sentiment_model=sentiment_model,
            category_model=category_model,
        )
    return _cached_pipeline.analyze_feedback(text)
