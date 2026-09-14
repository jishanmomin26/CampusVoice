"""Comprehensive Unit and Integration Tests for Category Classification Models.

Validates:
  1. Category training & test dataset loading
  2. Required columns and six canonical categories
  3. No null clean_text values
  4. Training of Logistic Regression and MultinomialNB
  5. Valid canonical category predictions covering full test set
  6. Dynamic evaluation metrics & 6x6 confusion matrix sum (cm.sum() == len(y_test))
  7. Data leakage prevention: vectorizer is loaded, not refitted, vocabulary size matches features dynamically
  8. Model selection logic strictly based on Macro F1
  9. Loading of serialized models and best_category_model.joblib
  10. End-to-end category inference and negation preservation
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure project roots are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from ml.evaluation.evaluate_category_models import (
    CANONICAL_CATEGORIES,
    compare_and_select_best_category_model,
    evaluate_category_model,
)
from ml.models.category_inference import get_category_model, predict_category
from ml.training.train_category_models import (
    load_category_data,
    load_tfidf_vectorizer,
    prepare_category_features,
    train_logistic_regression,
    train_multinomial_nb,
)


@pytest.fixture(scope="module")
def category_dataset():
    """Loads and returns train and test DataFrames."""
    return load_category_data()


@pytest.fixture(scope="module")
def prepared_features(category_dataset):
    """Loads vectorizer and extracts train/test feature matrices."""
    train_df, test_df = category_dataset
    vectorizer = load_tfidf_vectorizer()
    X_train, y_train, X_test, y_test = prepare_category_features(train_df, test_df, vectorizer)
    return train_df, test_df, vectorizer, X_train, y_train, X_test, y_test


class TestCategoryDatasetLoadingAndValidation:
    """Tests loading, columns, and canonical category distributions."""

    def test_datasets_load_successfully(self, category_dataset):
        train_df, test_df = category_dataset
        assert train_df is not None
        assert test_df is not None
        assert len(train_df) > 0
        assert len(test_df) > 0

    def test_required_columns_exist(self, category_dataset):
        train_df, test_df = category_dataset
        required = {"clean_text", "category"}
        assert required.issubset(train_df.columns)
        assert required.issubset(test_df.columns)

    def test_exactly_six_canonical_categories_present(self, category_dataset):
        train_df, test_df = category_dataset
        canonical_set = set(CANONICAL_CATEGORIES)
        assert len(canonical_set) == 6

        train_cats = set(train_df["category"].dropna().unique())
        test_cats = set(test_df["category"].dropna().unique())

        assert train_cats == canonical_set, f"Unexpected train categories: {train_cats - canonical_set}"
        assert test_cats == canonical_set, f"Unexpected test categories: {test_cats - canonical_set}"

    def test_no_missing_clean_text_values(self, category_dataset):
        train_df, test_df = category_dataset
        assert not train_df["clean_text"].isnull().any()
        assert not test_df["clean_text"].isnull().any()
        assert (train_df["clean_text"].astype(str).str.strip() != "").all()
        assert (test_df["clean_text"].astype(str).str.strip() != "").all()


class TestDataLeakageAndTfidfFeatures:
    """Tests that TF-IDF is loaded, not refitted, and feature dimensions match dynamically."""

    def test_vectorizer_is_not_refitted_and_dimensions_match_dynamically(self, prepared_features):
        _, _, vectorizer, X_train, y_train, X_test, y_test = prepared_features

        vocab_len = len(vectorizer.vocabulary_)
        # Dynamic verification as per user adjustment 2:
        assert X_train.shape[1] == vocab_len
        assert X_test.shape[1] == X_train.shape[1]
        assert X_train.shape[0] == len(y_train)
        assert X_test.shape[0] == len(y_test)

    def test_vocabulary_remains_unchanged(self, prepared_features):
        _, _, vectorizer, _, _, _, _ = prepared_features
        initial_vocab = dict(vectorizer.vocabulary_)
        # Vectorize new text sample to simulate inference
        vectorizer.transform(["sample feedback text"])
        assert vectorizer.vocabulary_ == initial_vocab


class TestModelTrainingAndPredictions:
    """Tests training of Logistic Regression and MultinomialNB."""

    def test_logistic_regression_trains_and_predicts_valid_categories(self, prepared_features):
        _, _, _, X_train, y_train, X_test, y_test = prepared_features
        model = train_logistic_regression(X_train, y_train)

        assert model is not None
        assert model.class_weight is None  # Unweighted as requested

        y_pred = model.predict(X_test)
        assert len(y_pred) == len(y_test)

        # All predictions must belong to canonical categories
        unique_preds = set(y_pred)
        assert unique_preds.issubset(set(CANONICAL_CATEGORIES))

    def test_multinomial_nb_trains_and_predicts_valid_categories(self, prepared_features):
        _, _, _, X_train, y_train, X_test, y_test = prepared_features
        model = train_multinomial_nb(X_train, y_train)

        assert model is not None
        assert model.alpha == 1.0

        y_pred = model.predict(X_test)
        assert len(y_pred) == len(y_test)

        unique_preds = set(y_pred)
        assert unique_preds.issubset(set(CANONICAL_CATEGORIES))


class TestModelEvaluationAndSelection:
    """Tests evaluation metrics, 6x6 confusion matrix dynamic sums, and Macro F1 selection."""

    def test_evaluation_metrics_bounds_and_structure(self, prepared_features):
        _, _, _, X_train, y_train, X_test, y_test = prepared_features
        model = train_logistic_regression(X_train, y_train)
        metrics = evaluate_category_model(model, X_test, y_test, CANONICAL_CATEGORIES)

        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["f1_macro"] <= 1.0
        assert 0.0 <= metrics["precision_macro"] <= 1.0
        assert 0.0 <= metrics["recall_macro"] <= 1.0
        assert 0.0 <= metrics["f1_weighted"] <= 1.0

        # Check per-category metrics exist for all 6 categories
        assert len(metrics["per_category"]) == 6
        for cat in CANONICAL_CATEGORIES:
            assert cat in metrics["per_category"]
            assert 0.0 <= metrics["per_category"][cat]["f1_score"] <= 1.0

    def test_confusion_matrix_shape_and_dynamic_sum(self, prepared_features):
        _, _, _, X_train, y_train, X_test, y_test = prepared_features
        model = train_logistic_regression(X_train, y_train)
        metrics = evaluate_category_model(model, X_test, y_test, CANONICAL_CATEGORIES)

        cm_matrix = np.array(metrics["confusion_matrix"]["matrix"])
        # Exactly 6x6
        assert cm_matrix.shape == (6, 6)

        # Dynamic verification (DO NOT hardcode 145)
        assert cm_matrix.sum() == len(y_test)

    def test_model_selection_logic_prefers_higher_macro_f1(self):
        mock_eval = {
            "model_a": {
                "accuracy": 0.90,
                "f1_macro": 0.65,
                "precision_macro": 0.70,
                "recall_macro": 0.62,
                "f1_weighted": 0.88,
                "precision_weighted": 0.89,
                "recall_weighted": 0.90,
            },
            "model_b": {
                "accuracy": 0.85,
                "f1_macro": 0.75,  # Higher Macro F1
                "precision_macro": 0.74,
                "recall_macro": 0.76,
                "f1_weighted": 0.84,
                "precision_weighted": 0.84,
                "recall_weighted": 0.85,
            },
        }
        selection = compare_and_select_best_category_model(mock_eval)
        assert selection["best_model"] == "model_b"
        assert selection["selected_metric"] == "f1_macro"
        assert selection["best_macro_f1"] == 0.75


class TestSerializedArtifactsAndInference:
    """Tests loading serialized models and end-to-end category inference."""

    def test_can_load_all_serialized_models(self):
        for name in ["logistic_regression", "naive_bayes", "best"]:
            model = get_category_model(name)
            assert model is not None
            assert hasattr(model, "predict")

    def test_category_inference_returns_required_fields(self):
        result = predict_category("The laboratory equipment is not functioning well.", model_name="best")

        assert "category" in result
        assert "confidence" in result
        assert "clean_text" in result
        assert "model_used" in result
        assert "probabilities" in result

        assert result["category"] in CANONICAL_CATEGORIES
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

        # Probabilities cover all 6 categories
        assert isinstance(result["probabilities"], dict)
        assert len(result["probabilities"]) == 6
        prob_sum = sum(result["probabilities"].values())
        assert pytest.approx(prob_sum, rel=1e-3) == 1.0

    def test_best_category_model_joblib_can_be_loaded(self):
        import joblib
        best_model_path = BASE_DIR / "ml" / "models" / "best_category_model.joblib"
        assert best_model_path.exists(), f"File does not exist: {best_model_path}"
        loaded_model = joblib.load(best_model_path)
        assert loaded_model is not None
        assert hasattr(loaded_model, "predict")

    def test_inference_preserves_step3_negation_preprocessing(self):
        result = predict_category("The faculty was not helpful during lectures.", model_name="best")
        # Step 3 negation preservation guarantees 'not' remains in clean_text
        assert "not" in result["clean_text"].lower().split()
