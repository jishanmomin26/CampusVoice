"""Comprehensive Unit Tests for Model Training, Evaluation, and Inference."""

import sys
from pathlib import Path
import numpy as np
import pytest

# Add project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from ml.evaluation.evaluate_models import compare_and_select_best_model, evaluate_model
from ml.models.inference import get_model, predict_sentiment
from ml.training.train_models import (
    load_training_data,
    train_logistic_regression,
    train_multinomial_nb,
)


@pytest.fixture(scope="module")
def dataset_data():
    """Loads training and testing data fixture."""
    return load_training_data()


class TestModelTraining:
    """Tests training and prediction validity for candidate models."""

    def test_logistic_regression_trains_and_predicts_valid_classes(self, dataset_data):
        X_train, X_test, y_train, y_test, _ = dataset_data
        model = train_logistic_regression(X_train, y_train, max_iter=2000, random_state=42)

        preds = model.predict(X_test)
        unique_preds = set(preds)
        valid_labels = {-1, 0, 1}

        # Predictions must strictly be subset of valid classes
        assert unique_preds.issubset(valid_labels)
        assert len(preds) == len(y_test)

    def test_multinomial_nb_trains_and_predicts_valid_classes(self, dataset_data):
        X_train, X_test, y_train, y_test, _ = dataset_data
        model = train_multinomial_nb(X_train, y_train, alpha=1.0)

        preds = model.predict(X_test)
        unique_preds = set(preds)
        valid_labels = {-1, 0, 1}

        assert unique_preds.issubset(valid_labels)
        assert len(preds) == len(y_test)


class TestModelEvaluation:
    """Tests evaluation metrics, confusion matrix dimensions, and dynamic totals."""

    def test_evaluation_metrics_structure_and_bounds(self, dataset_data):
        X_train, X_test, y_train, y_test, _ = dataset_data
        model = train_logistic_regression(X_train, y_train, max_iter=2000, random_state=42)
        metrics = evaluate_model(model, X_test, y_test)

        # Accuracy & F1 bounds
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["f1_macro"] <= 1.0
        assert 0.0 <= metrics["f1_weighted"] <= 1.0
        assert 0.0 <= metrics["precision_macro"] <= 1.0
        assert 0.0 <= metrics["recall_macro"] <= 1.0

        # Per-class metric completeness
        for label_name in ["negative", "neutral", "positive"]:
            assert label_name in metrics["per_class"]
            cls_stat = metrics["per_class"][label_name]
            assert 0.0 <= cls_stat["precision"] <= 1.0
            assert 0.0 <= cls_stat["recall"] <= 1.0
            assert 0.0 <= cls_stat["f1_score"] <= 1.0
            assert cls_stat["support"] > 0

    def test_confusion_matrix_shape_and_dynamic_sum(self, dataset_data):
        """Verify confusion matrix is 3x3 and sums dynamically to test size (no hard-coding)."""
        X_train, X_test, y_train, y_test, _ = dataset_data
        model = train_multinomial_nb(X_train, y_train, alpha=1.0)
        metrics = evaluate_model(model, X_test, y_test)

        cm = np.array(metrics["confusion_matrix"]["matrix"])
        # Dimensions check
        assert cm.shape == (3, 3)

        # Dynamic sum check (strictly equal to len(y_test))
        assert cm.sum() == len(y_test)
        assert metrics["support_total"] == len(y_test)

    def test_model_selection_logic(self):
        fake_results = {
            "model_a": {"f1_macro": 0.55, "accuracy": 0.70, "f1_weighted": 0.68, "precision_macro": 0.56, "recall_macro": 0.55},
            "model_b": {"f1_macro": 0.63, "accuracy": 0.72, "f1_weighted": 0.71, "precision_macro": 0.64, "recall_macro": 0.62},
        }
        best_name, comparison = compare_and_select_best_model(fake_results)
        assert best_name == "model_b"
        assert comparison["best_macro_f1"] == 0.63


class TestArtifactLoadingAndInference:
    """Tests loading serialized models and executing sentiment predictions."""

    def test_can_load_all_serialized_models(self):
        lr = get_model("logistic_regression")
        nb = get_model("naive_bayes")
        best = get_model("best")

        assert lr is not None
        assert nb is not None
        assert best is not None

    def test_inference_returns_required_fields_and_probabilities(self):
        text = "The faculty explains difficult concepts clearly and is very supportive."
        res = predict_sentiment(text, model_name="best")

        assert "text" in res
        assert "clean_text" in res
        assert "sentiment" in res
        assert "sentiment_label" in res
        assert "model_used" in res
        assert "probabilities" in res
        assert "confidence" in res

        assert res["sentiment"] in (-1, 0, 1)
        assert res["sentiment_label"] in ("negative", "neutral", "positive")
        assert res["confidence"] > 0.0
        assert sum(res["probabilities"].values()) == pytest.approx(1.0, rel=1e-2)

    def test_inference_preserves_negation_preprocessing(self):
        text = "The faculty is not helpful."
        res = predict_sentiment(text, model_name="best")

        # Must retain 'not' in clean_text
        assert "not" in res["clean_text"].split()
        assert res["clean_text"] != "faculty helpful"
