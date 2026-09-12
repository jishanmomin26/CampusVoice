"""Comprehensive Unit Tests for Dataset Preparation & TF-IDF Pipeline."""

import sys
from pathlib import Path
import pandas as pd
import pytest

# Ensure project roots are in path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from preprocessing.dataset_preparation import (
    CATEGORY_COLUMN_PAIRS,
    SENTIMENT_LABEL_MAP,
    apply_nlp_preprocessing_to_dataframe,
    load_raw_dataset,
    split_dataset,
    transform_wide_to_long,
    validate_and_clean_dataset,
)
from preprocessing.tfidf_features import (
    create_tfidf_vectorizer,
    fit_and_transform_features,
    load_vectorizer,
    save_vectorizer,
)

RAW_DATASET_PATH = ML_DIR / "datasets" / "finalDataset0.2.xlsx"


class TestDatasetLoadingAndStructure:
    """Tests loading and structural validation of the raw dataset."""

    def test_raw_dataset_file_exists(self):
        assert RAW_DATASET_PATH.exists(), f"Source file {RAW_DATASET_PATH} must exist."

    def test_load_raw_dataset_validates_12_columns(self):
        df = load_raw_dataset(RAW_DATASET_PATH)
        assert df.shape[1] == 12, f"Expected 12 columns, found {df.shape[1]}"
        assert df.shape[0] >= 180, "Expected at least 180 survey response rows."

    def test_rejects_invalid_column_count(self, tmp_path):
        dummy_file = tmp_path / "bad.xlsx"
        bad_df = pd.DataFrame({"col1": [1], "col2": [2]})
        bad_df.to_excel(dummy_file, index=False)

        with pytest.raises(ValueError, match="expected exactly 12 columns"):
            load_raw_dataset(dummy_file)


class TestWideToLongTransformation:
    """Tests unpivoting and category pairing logic."""

    @pytest.fixture
    def sample_wide_df(self):
        # Create a 2-row synthetic wide DataFrame matching exact column positions
        data = {
            "s1": [1, 0],
            "t1": ["Great teacher", "Average lecture"],
            "s2": [-1, 1],
            "t2": ["Outdated syllabus", "Relevant content"],
            "s3": [0, 1],
            "t3": ["Fair exam", "Easy paper"],
            "s4": [1, -1],
            "t4": ["Good lab", "Slow computers"],
            "s5": [1, 0],
            "t5": ["Quiet library", "Limited seating"],
            "s6": [-1, 1],
            "t6": ["No clubs", "Fun sports"],
        }
        return pd.DataFrame(data)

    def test_transformation_shape_and_categories(self, sample_wide_df):
        long_df = transform_wide_to_long(sample_wide_df)
        # 2 rows * 6 categories = 12 unpivoted records
        assert len(long_df) == 12
        assert set(long_df.columns) == {
            "original_row_idx",
            "category",
            "sentiment_raw",
            "feedback_text_raw",
        }

        expected_cats = {pair[2] for pair in CATEGORY_COLUMN_PAIRS}
        assert set(long_df["category"].unique()) == expected_cats


class TestDataValidationAndDeduplication:
    """Tests data cleaning, sentiment mapping, and category-aware deduplication."""

    def test_filters_empty_text_and_invalid_sentiments(self):
        dirty_data = pd.DataFrame([
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": "Valid feedback"},
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": ""},  # empty text
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": "   "},  # whitespace only
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": None},  # NaN text
            {"category": "Teaching", "sentiment_raw": 99, "feedback_text_raw": "Bad sentiment"},  # invalid sent
            {"category": "Teaching", "sentiment_raw": "invalid", "feedback_text_raw": "Non-numeric sent"},
        ])

        clean_df, audit = validate_and_clean_dataset(dirty_data)
        assert len(clean_df) == 1
        assert clean_df.iloc[0]["feedback_text"] == "Valid feedback"
        assert audit["removed_empty_text"] == 3
        assert audit["removed_invalid_sentiment"] == 2

    def test_sentiment_label_mapping(self):
        data = pd.DataFrame([
            {"category": "Teaching", "sentiment_raw": -1, "feedback_text_raw": "Negative text"},
            {"category": "Teaching", "sentiment_raw": 0, "feedback_text_raw": "Neutral text"},
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": "Positive text"},
        ])
        clean_df, _ = validate_and_clean_dataset(data)

        label_map = dict(zip(clean_df["sentiment"], clean_df["sentiment_label"]))
        assert label_map[-1] == "negative"
        assert label_map[0] == "neutral"
        assert label_map[1] == "positive"

    def test_category_aware_deduplication(self):
        """Identical text in DIFFERENT categories must be retained; same category must be deduplicated."""
        data = pd.DataFrame([
            # Duplicate within Teaching
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": "Good"},
            {"category": "Teaching", "sentiment_raw": 1, "feedback_text_raw": "Good"},
            # Same text in Examination -> MUST BE RETAINED!
            {"category": "Examination", "sentiment_raw": 1, "feedback_text_raw": "Good"},
        ])
        clean_df, audit = validate_and_clean_dataset(data)
        assert len(clean_df) == 2
        assert audit["removed_duplicates"] == 1
        assert len(clean_df[clean_df["category"] == "Teaching"]) == 1
        assert len(clean_df[clean_df["category"] == "Examination"]) == 1


class TestNLPPipelineAndSplitting:
    """Tests integration of Step 3 NLP and stratified splitting."""

    def test_nlp_preprocessing_preserves_negation(self):
        sample_df = pd.DataFrame([
            {"id": 1, "category": "Teaching", "sentiment": -1, "sentiment_label": "negative", "feedback_text": "The faculty is not helpful."},
        ])
        processed_df = apply_nlp_preprocessing_to_dataframe(sample_df)
        assert "clean_text" in processed_df.columns
        clean = processed_df.iloc[0]["clean_text"]
        assert "not" in clean.split(), "Negation 'not' must be retained in clean_text"
        assert clean != "faculty helpful"

    def test_stratified_train_test_split_reproducibility(self):
        # Create a sample DataFrame with 50 rows and mixed sentiments
        rows = []
        for i in range(50):
            sent = 1 if i < 25 else (-1 if i < 40 else 0)
            rows.append({
                "id": i + 1,
                "category": "Teaching",
                "sentiment": sent,
                "sentiment_label": SENTIMENT_LABEL_MAP[sent],
                "feedback_text": f"Feedback number {i}",
                "clean_text": f"feedback number {i}",
            })
        df = pd.DataFrame(rows)

        train_df1, test_df1 = split_dataset(df, test_size=0.2, random_state=42)
        train_df2, test_df2 = split_dataset(df, test_size=0.2, random_state=42)

        # Reproducibility check
        pd.testing.assert_frame_equal(train_df1, train_df2)
        pd.testing.assert_frame_equal(test_df1, test_df2)

        # Proportions check (80/20)
        assert len(train_df1) == 40
        assert len(test_df1) == 10

        # Overlap check
        train_ids = set(train_df1["id"])
        test_ids = set(test_df1["id"])
        assert len(train_ids.intersection(test_ids)) == 0


class TestTfidfFeatureEngineering:
    """Tests TF-IDF vectorization, data leakage prevention, and artifact saving."""

    def test_no_data_leakage_in_tfidf(self):
        train_texts = pd.Series(["practical session useful", "good faculty explanation"])
        test_texts = pd.Series(["unseen novel words", "practical session"])

        vectorizer = create_tfidf_vectorizer(ngram_range=(1, 2), min_df=1)
        X_train, X_test, meta = fit_and_transform_features(vectorizer, train_texts, test_texts)

        train_vocab = set(vectorizer.get_feature_names_out())

        # Test words "unseen" and "novel" must NOT be in the vectorizer vocabulary
        assert "unseen" not in train_vocab
        assert "novel" not in train_vocab

        # Shapes must match sample counts
        assert X_train.shape[0] == 2
        assert X_test.shape[0] == 2
        assert X_train.shape[1] == X_test.shape[1] == len(train_vocab)

    def test_vectorizer_serialization_roundtrip(self, tmp_path):
        train_texts = ["quick test sentence", "another training example"]
        vec = create_tfidf_vectorizer(ngram_range=(1, 2), min_df=1)
        vec.fit(train_texts)

        model_file = tmp_path / "test_vec.joblib"
        save_vectorizer(vec, model_file)
        assert model_file.exists()

        loaded_vec = load_vectorizer(model_file)
        assert loaded_vec.ngram_range == vec.ngram_range
        assert loaded_vec.min_df == vec.min_df
        assert list(loaded_vec.get_feature_names_out()) == list(vec.get_feature_names_out())
