"""Inference Module for CampusVoice Feedback Category Classification.

Loads serialized category models and vectorizer to predict student feedback category
using the Step 3 NLP preprocessing pipeline and Step 4 TF-IDF features.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
import joblib

# Ensure backend and ml directories are on sys.path
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

# In-memory caches for fast repeated inference
_cached_vectorizer = None
_cached_models: Dict[str, Any] = {}


def get_vectorizer():
    """Loads and caches the fitted TF-IDF vectorizer."""
    global _cached_vectorizer
    if _cached_vectorizer is None:
        vec_path = MODELS_DIR / "tfidf_vectorizer.joblib"
        if not vec_path.exists():
            raise FileNotFoundError(f"TF-IDF vectorizer artifact not found at: {vec_path}")
        _cached_vectorizer = joblib.load(vec_path)
    return _cached_vectorizer


def get_category_model(model_name: str = "best"):
    """Loads and caches a requested category classification model.

    Args:
        model_name: One of 'best', 'logistic_regression', 'naive_bayes'.

    Returns:
        Fitted scikit-learn classifier.
    """
    global _cached_models
    model_name = model_name.lower().strip()

    filename_map = {
        "best": "best_category_model.joblib",
        "default": "best_category_model.joblib",
        "logistic_regression": "logistic_regression_category.joblib",
        "naive_bayes": "naive_bayes_category.joblib",
        "multinomial_nb": "naive_bayes_category.joblib",
    }

    if model_name not in filename_map:
        raise ValueError(
            f"Unknown model '{model_name}'. Choose from: 'best', 'logistic_regression', 'naive_bayes'."
        )

    target_file = filename_map[model_name]
    if target_file not in _cached_models:
        model_path = MODELS_DIR / target_file
        if not model_path.exists():
            raise FileNotFoundError(f"Category model artifact not found at: {model_path}")
        _cached_models[target_file] = joblib.load(model_path)

    return _cached_models[target_file]


def predict_category(text: str, model_name: str = "best") -> Dict[str, Any]:
    """Predicts feedback category for raw student feedback text.

    Args:
        text: Raw student feedback string.
        model_name: Model to use ('best', 'logistic_regression', or 'naive_bayes').

    Returns:
        Dict[str, Any]: Prediction result containing:
            - text: Original text
            - clean_text: Preprocessed text with negations preserved
            - category: Predicted category name
            - confidence: Highest predicted class probability (if available)
            - model_used: Model identifier
            - probabilities: Class probability breakdown across all 6 categories
    """
    model = get_category_model(model_name)
    vectorizer = get_vectorizer()

    # Step 3 NLP Preprocessing (preserves negations)
    prep_result = preprocess_text(text)
    clean_text = prep_result.clean_text

    # Vectorize cleaned text (single sample matrix)
    X_vec = vectorizer.transform([clean_text])

    # Predict category label
    pred_category = str(model.predict(X_vec)[0])

    # Predict probabilities if supported
    probabilities = None
    confidence = None
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_vec)[0]
        classes = model.classes_
        probabilities = {
            str(cls): float(prob)
            for cls, prob in zip(classes, probs)
        }
        confidence = float(max(probs))

    return {
        "text": text,
        "clean_text": clean_text,
        "category": pred_category,
        "confidence": confidence,
        "model_used": model_name,
        "probabilities": probabilities,
    }
