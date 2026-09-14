"""Comprehensive Unit and Integration Tests for the Unified Feedback Intelligence Pipeline.

Validates 25 Step 7 base conditions + 16 Step 8.2 priority integration conditions:
  1. Pipeline initializes successfully
  2. All required artifacts load into memory
  3. Valid feedback produces a structured result dictionary
  4. Sentiment prediction contains required fields
  5. Category prediction contains required fields
  6. Sentiment label belongs strictly to {-1, 0, 1}
  7. Sentiment name matches the numeric label
  8. Category belongs to the canonical six categories
  9. Sentiment probabilities are valid [0, 1]
  10. Category probabilities are valid [0, 1] across all 6 categories
  11. Probability distributions sum approximately to 1.0
  12. Confidence values are strictly bounded in [0, 1]
  13. Empty string input is rejected with ValueError
  14. Whitespace-only input is rejected with ValueError
  15. Non-string and None inputs are rejected with TypeError/ValueError
  16. Negation preprocessing is preserved in clean_text
  17. Repeated inference calls execute stably
  18. Model-specific inference works for Logistic Regression
  19. Model-specific inference works for Naive Bayes
  20. Missing artifact errors are actionable and raise FileNotFoundError
  21. Invalid model names are rejected with ValueError
  22. TF-IDF vocabulary is never modified during inference
  23. Vectorizer feature dimensions remain strictly unchanged
  24. TF-IDF transformation behavior (transform called, fit/fit_transform never called)
  25. In-memory model caching maintains identical object references without disk reloading

Step 8.2 Priority Integration Conditions:
  26. Normal pipeline output contains 'priority' field
  27. Priority contains 'score', 'level', and 'reason'
  28. Priority score is an integer bounded in [0, 100]
  29. Priority level belongs to {'High', 'Medium', 'Low'}
  30. Priority reason is a non-empty string
  31. Priority values are derived from actual pipeline sentiment and category outputs
  32. Negative high-confidence case produces High priority
  33. Positive case produces Low priority
  34. Priority calculation is deterministic across repeated calls
  35. Sentiment output schema and values remain unchanged
  36. Category output schema and values remain unchanged
  37. Model-specific inference (Logistic Regression) includes priority
  38. Model-specific inference (Naive Bayes) includes priority
  39. Invalid input validation remains unchanged
  40. TF-IDF transform-only behavior remains unchanged with priority
  41. calculate_from_intelligence integration matches pipeline output
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure project base directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from ml.pipeline.feedback_intelligence import (
    CANONICAL_CATEGORIES,
    LABEL_TO_SENTIMENT,
    FeedbackIntelligencePipeline,
    analyze_feedback,
)
from ml.priority.priority_scoring import PriorityScorer


@pytest.fixture(scope="module")
def default_pipeline():
    """Initializes and returns a default unified pipeline fixture."""
    return FeedbackIntelligencePipeline(sentiment_model="best", category_model="best")


class TestPipelineInitializationAndArtifacts:
    """Validates pipeline initialization and in-memory artifact loading (Conditions 1-2)."""

    def test_condition_1_pipeline_initializes_successfully(self, default_pipeline):
        """Condition 1: Pipeline initializes without raising exceptions."""
        assert default_pipeline is not None
        assert isinstance(default_pipeline, FeedbackIntelligencePipeline)

    def test_condition_2_all_required_artifacts_loaded(self, default_pipeline):
        """Condition 2: TF-IDF vectorizer, sentiment model, and category model are loaded."""
        assert default_pipeline._vectorizer is not None
        assert default_pipeline._sentiment_model is not None
        assert default_pipeline._category_model is not None
        assert hasattr(default_pipeline._vectorizer, "transform")
        assert hasattr(default_pipeline._sentiment_model, "predict")
        assert hasattr(default_pipeline._category_model, "predict")


class TestOutputStructureAndContract:
    """Validates output structure and field completeness (Conditions 3-5)."""

    def test_condition_3_valid_feedback_produces_structured_result(self, default_pipeline):
        """Condition 3: Valid feedback returns dict with all top-level keys."""
        sample = "The professors are knowledgeable and provide great guidance."
        result = default_pipeline.analyze_feedback(sample)

        assert isinstance(result, dict)
        required_keys = {"feedback", "clean_text", "sentiment", "category", "models"}
        assert required_keys.issubset(result.keys())
        assert result["feedback"] == sample
        assert isinstance(result["clean_text"], str)

    def test_condition_4_sentiment_contains_required_fields(self, default_pipeline):
        """Condition 4: Sentiment sub-dict contains label, name, confidence, probabilities."""
        result = default_pipeline.analyze_feedback("Great course structure!")
        sentiment = result["sentiment"]

        assert "label" in sentiment
        assert "name" in sentiment
        assert "confidence" in sentiment
        assert "probabilities" in sentiment

    def test_condition_5_category_contains_required_fields(self, default_pipeline):
        """Condition 5: Category sub-dict contains name, confidence, probabilities."""
        result = default_pipeline.analyze_feedback("Lab equipment needs maintenance.")
        category = result["category"]

        assert "name" in category
        assert "confidence" in category
        assert "probabilities" in category


class TestSentimentAndCategoryValidity:
    """Validates predictions against canonical sets and metric bounds (Conditions 6-12)."""

    def test_condition_6_sentiment_label_in_valid_set(self, default_pipeline):
        """Condition 6: Sentiment numeric label must be in {-1, 0, 1}."""
        result = default_pipeline.analyze_feedback("Good laboratory environment.")
        assert result["sentiment"]["label"] in {-1, 0, 1}

    def test_condition_7_sentiment_name_matches_numeric_label(self, default_pipeline):
        """Condition 7: Sentiment name string matches canonical mapping of numeric label."""
        result = default_pipeline.analyze_feedback("Satisfactory learning experience.")
        label = result["sentiment"]["label"]
        name = result["sentiment"]["name"]
        assert name == LABEL_TO_SENTIMENT[label]

    def test_condition_8_category_in_canonical_six_categories(self, default_pipeline):
        """Condition 8: Category name belongs strictly to the six canonical categories."""
        result = default_pipeline.analyze_feedback("The exam schedule was published on time.")
        assert result["category"]["name"] in CANONICAL_CATEGORIES

    def test_condition_9_sentiment_probabilities_valid(self, default_pipeline):
        """Condition 9: Each sentiment probability value is in [0.0, 1.0]."""
        result = default_pipeline.analyze_feedback("The library resources are adequate.")
        probs = result["sentiment"]["probabilities"]
        assert isinstance(probs, dict)
        for val in probs.values():
            assert 0.0 <= val <= 1.0

    def test_condition_10_category_probabilities_valid(self, default_pipeline):
        """Condition 10: Category probabilities cover all 6 categories, each in [0.0, 1.0]."""
        result = default_pipeline.analyze_feedback("Extracurricular sports should be organized.")
        probs = result["category"]["probabilities"]
        assert isinstance(probs, dict)
        assert len(probs) == 6
        for cat in CANONICAL_CATEGORIES:
            assert cat in probs
            assert 0.0 <= probs[cat] <= 1.0

    def test_condition_11_probability_sums_approximate_one(self, default_pipeline):
        """Condition 11: Sentiment and category probability distributions sum to ~1.0."""
        result = default_pipeline.analyze_feedback("Interactive workshops and seminars.")
        s_probs = result["sentiment"]["probabilities"]
        c_probs = result["category"]["probabilities"]

        assert pytest.approx(sum(s_probs.values()), rel=1e-3) == 1.0
        assert pytest.approx(sum(c_probs.values()), rel=1e-3) == 1.0

    def test_condition_12_confidence_values_between_zero_and_one(self, default_pipeline):
        """Condition 12: Both sentiment and category confidence scores are in [0.0, 1.0]."""
        result = default_pipeline.analyze_feedback("Comprehensive textbook availability.")
        assert 0.0 <= result["sentiment"]["confidence"] <= 1.0
        assert 0.0 <= result["category"]["confidence"] <= 1.0


class TestInputValidationAndRobustness:
    """Validates input rejection and error boundaries (Conditions 13-15)."""

    def test_condition_13_empty_input_rejected(self, default_pipeline):
        """Condition 13: Empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            default_pipeline.analyze_feedback("")

    def test_condition_14_whitespace_input_rejected(self, default_pipeline):
        """Condition 14: Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            default_pipeline.analyze_feedback("     \n\t  ")

    def test_condition_15_non_string_input_rejected(self, default_pipeline):
        """Condition 15: Non-string and None inputs raise TypeError or ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            default_pipeline.analyze_feedback(None)

        with pytest.raises(TypeError, match="must be a string"):
            default_pipeline.analyze_feedback(12345)

        with pytest.raises(TypeError, match="must be a string"):
            default_pipeline.analyze_feedback(["Great teaching"])


class TestNegationAndRepeatedInference:
    """Validates linguistic negation and execution stability (Conditions 16-17)."""

    def test_condition_16_negation_preprocessing_preserved(self, default_pipeline):
        """Condition 16: 'The faculty is not helpful.' preserves 'not' in clean_text."""
        sample = "The faculty is not helpful."
        result = default_pipeline.analyze_feedback(sample)

        assert "not" in result["clean_text"].lower().split()
        assert result["sentiment"]["label"] in {-1, 0, 1}
        assert result["category"]["name"] in CANONICAL_CATEGORIES

    def test_condition_17_repeated_inference_calls_work_correctly(self, default_pipeline):
        """Condition 17: Repeated calls maintain stability and consistent structure."""
        samples = [
            "Good course outline.",
            "Computers in lab are slow.",
            "Examinations are fair and clear.",
        ]
        for s in samples:
            res = default_pipeline.analyze_feedback(s)
            assert res["feedback"] == s
            assert res["sentiment"]["name"] in {"negative", "neutral", "positive"}
            assert res["category"]["name"] in CANONICAL_CATEGORIES


class TestModelOptionsAndConfiguration:
    """Validates model-specific selection options (Conditions 18-19)."""

    def test_condition_18_model_specific_inference_logistic_regression(self):
        """Condition 18: Logistic Regression configuration loads and predicts."""
        pipeline = FeedbackIntelligencePipeline(
            sentiment_model="logistic_regression",
            category_model="logistic_regression",
        )
        result = pipeline.analyze_feedback("Structured course syllabus.")
        assert result["models"]["sentiment"] == "logistic_regression"
        assert result["models"]["category"] == "logistic_regression"
        assert result["sentiment"]["label"] in {-1, 0, 1}
        assert result["category"]["name"] in CANONICAL_CATEGORIES

    def test_condition_19_model_specific_inference_naive_bayes(self):
        """Condition 19: Naive Bayes configuration loads and predicts."""
        pipeline = FeedbackIntelligencePipeline(
            sentiment_model="naive_bayes",
            category_model="naive_bayes",
        )
        result = pipeline.analyze_feedback("Books in library are helpful.")
        assert result["models"]["sentiment"] == "naive_bayes"
        assert result["models"]["category"] == "naive_bayes"
        assert result["sentiment"]["label"] in {-1, 0, 1}
        assert result["category"]["name"] in CANONICAL_CATEGORIES


class TestErrorHandlingAndEdgeCases:
    """Validates missing artifacts and invalid model options (Conditions 20-21)."""

    def test_condition_20_missing_artifact_errors_are_clear(self, tmp_path):
        """Condition 20: Missing artifact raises descriptive FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="artifact not found"):
            FeedbackIntelligencePipeline(models_dir=tmp_path)

    def test_condition_21_invalid_model_name_errors_are_clear(self):
        """Condition 21: Unsupported model name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sentiment model"):
            FeedbackIntelligencePipeline(sentiment_model="deep_transformer")

        with pytest.raises(ValueError, match="Invalid category model"):
            FeedbackIntelligencePipeline(category_model="svm_classifier")


class TestTfidfIntegrityAndDataLeakage:
    """Validates TF-IDF vectorizer immutability and reuse behavior (Conditions 22-24)."""

    def test_condition_22_tfidf_vocabulary_not_modified_during_inference(self, default_pipeline):
        """Condition 22: Vectorizer vocabulary remains identical before and after inference."""
        initial_vocab = dict(default_pipeline._vectorizer.vocabulary_)
        default_pipeline.analyze_feedback("Completely novel vocabulary term xyz123qwerty.")
        assert default_pipeline._vectorizer.vocabulary_ == initial_vocab

    def test_condition_23_vectorizer_feature_dimensions_remain_unchanged(self, default_pipeline):
        """Condition 23: Feature dimensions dynamically match vocabulary length."""
        vocab_len = len(default_pipeline._vectorizer.vocabulary_)
        X_vec = default_pipeline._vectorizer.transform(["standard feedback"])
        assert X_vec.shape[1] == vocab_len

    def test_condition_24_tfidf_reuse_and_no_refitting(self, default_pipeline):
        """Condition 24: Vectorizer is used via transform only; fit and fit_transform are never called."""
        vectorizer = default_pipeline._vectorizer

        # Monkey-patch fit and fit_transform to raise if called
        vectorizer.fit = MagicMock(side_effect=RuntimeError("fit() must not be called during inference"))
        vectorizer.fit_transform = MagicMock(
            side_effect=RuntimeError("fit_transform() must not be called during inference")
        )

        try:
            # Run inference; should succeed using transform() only
            result = default_pipeline.analyze_feedback("Excellent teaching pedagogy.")
            assert result is not None
            assert vectorizer.fit.call_count == 0
            assert vectorizer.fit_transform.call_count == 0
        finally:
            # Restore original vectorizer methods
            del vectorizer.fit
            del vectorizer.fit_transform


class TestModelCachingBehavior:
    """Validates in-memory model caching without redundant disk I/O (Condition 25)."""

    def test_condition_25_model_caching_reuses_in_memory_instances(self):
        """Condition 25: Repeated inference calls reuse identical in-memory model and vectorizer objects."""
        pipeline = FeedbackIntelligencePipeline()

        # Capture object identities (memory addresses)
        vec_id = id(pipeline._vectorizer)
        sent_id = id(pipeline._sentiment_model)
        cat_id = id(pipeline._category_model)

        # Run several inference calls
        pipeline.analyze_feedback("Teaching is clear.")
        pipeline.analyze_feedback("Labs need updated software.")
        pipeline.analyze_feedback("Library collection is great.")

        # Assert in-memory object references are strictly preserved (no disk reloading)
        assert id(pipeline._vectorizer) == vec_id
        assert id(pipeline._sentiment_model) == sent_id
        assert id(pipeline._category_model) == cat_id


class TestPriorityIntegration:
    """Validates Step 8.2 integration of PriorityScorer into FeedbackIntelligencePipeline."""

    def test_priority_field_present(self, default_pipeline):
        """Condition 1: Normal pipeline output contains a 'priority' field."""
        result = default_pipeline.analyze_feedback("The classrooms are well-ventilated.")
        assert "priority" in result
        assert isinstance(result["priority"], dict)

    def test_priority_contains_required_keys(self, default_pipeline):
        """Condition 2: Priority contains score, level, and reason."""
        result = default_pipeline.analyze_feedback("Great lab practical sessions.")
        priority = result["priority"]
        assert "score" in priority
        assert "level" in priority
        assert "reason" in priority

    def test_priority_score_integer_and_bounded(self, default_pipeline):
        """Condition 3: Priority score is an integer between 0 and 100."""
        result = default_pipeline.analyze_feedback("Examination schedules are clear.")
        score = result["priority"]["score"]
        assert isinstance(score, int)
        assert not isinstance(score, bool)
        assert 0 <= score <= 100

    def test_priority_level_valid_tier(self, default_pipeline):
        """Condition 4: Priority level is one of High, Medium, Low."""
        result = default_pipeline.analyze_feedback("The campus sports facilities are maintained.")
        level = result["priority"]["level"]
        assert level in {"High", "Medium", "Low"}

    def test_priority_reason_non_empty_string(self, default_pipeline):
        """Condition 5: Priority reason is a non-empty string."""
        result = default_pipeline.analyze_feedback("Good library environment.")
        reason = result["priority"]["reason"]
        assert isinstance(reason, str)
        assert len(reason.strip()) > 0

    def test_priority_derived_from_actual_sentiment_and_category(self, default_pipeline):
        """Condition 6: Priority values are derived from actual pipeline sentiment and category outputs."""
        result = default_pipeline.analyze_feedback("The faculty is approachable and helpful.")
        scorer = default_pipeline._priority_scorer

        expected = scorer.calculate(
            sentiment_name=result["sentiment"]["name"],
            sentiment_confidence=result["sentiment"]["confidence"],
            category_name=result["category"]["name"],
            category_confidence=result["category"]["confidence"],
        )
        assert result["priority"] == expected

    def test_negative_high_confidence_produces_high_priority_integration(self, default_pipeline):
        """Condition 7: Negative high-confidence signals produce High priority."""
        scorer = default_pipeline._priority_scorer
        payload = {
            "sentiment": {"name": "negative", "confidence": 0.85},
            "category": {"name": "Teaching", "confidence": 0.75},
        }
        computed = scorer.calculate_from_intelligence(payload)
        assert computed["level"] == "High"
        assert computed["score"] == 90

    def test_positive_case_produces_low_priority_integration(self, default_pipeline):
        """Condition 8: Positive case produces Low priority according to Step 8.1 rules."""
        result = default_pipeline.analyze_feedback(
            "There should be more technical hackathons and cultural extracurricular activities."
        )
        assert result["sentiment"]["name"] == "positive"
        assert result["priority"]["level"] == "Low"

    def test_priority_determinism_across_repeated_calls(self, default_pipeline):
        """Condition 9: Priority calculation is deterministic across repeated inference calls."""
        text = "The laboratory computers are outdated and the equipment is not functioning well."
        res1 = default_pipeline.analyze_feedback(text)
        res2 = default_pipeline.analyze_feedback(text)
        res3 = default_pipeline.analyze_feedback(text)

        assert res1["priority"] == res2["priority"] == res3["priority"]

    def test_existing_sentiment_output_unchanged(self, default_pipeline):
        """Condition 10: Existing Step 7 sentiment output schema and values remain unchanged."""
        result = default_pipeline.analyze_feedback("Library collection is extensive.")
        sent = result["sentiment"]
        assert set(sent.keys()) == {"label", "name", "confidence", "probabilities"}
        assert sent["label"] in {-1, 0, 1}
        assert 0.0 <= sent["confidence"] <= 1.0
        assert isinstance(sent["probabilities"], dict)

    def test_existing_category_output_unchanged(self, default_pipeline):
        """Condition 11: Existing Step 7 category output schema and values remain unchanged."""
        result = default_pipeline.analyze_feedback("Library collection is extensive.")
        cat = result["category"]
        assert set(cat.keys()) == {"name", "confidence", "probabilities"}
        assert cat["name"] in CANONICAL_CATEGORIES
        assert 0.0 <= cat["confidence"] <= 1.0
        assert len(cat["probabilities"]) == 6

    def test_model_specific_inference_priority_logistic_regression(self):
        """Condition 12a: Logistic Regression pipeline includes priority correctly."""
        pipeline = FeedbackIntelligencePipeline(
            sentiment_model="logistic_regression",
            category_model="logistic_regression",
        )
        result = pipeline.analyze_feedback("The syllabus should include cloud computing.")
        assert "priority" in result
        assert result["priority"]["level"] in {"High", "Medium", "Low"}

    def test_model_specific_inference_priority_naive_bayes(self):
        """Condition 12b: Naive Bayes pipeline includes priority correctly."""
        pipeline = FeedbackIntelligencePipeline(
            sentiment_model="naive_bayes",
            category_model="naive_bayes",
        )
        result = pipeline.analyze_feedback("The syllabus should include cloud computing.")
        assert "priority" in result
        assert result["priority"]["level"] in {"High", "Medium", "Low"}

    def test_invalid_inputs_still_rejected(self, default_pipeline):
        """Condition 13: Existing invalid-input validation remains unchanged."""
        with pytest.raises(ValueError, match="cannot be empty"):
            default_pipeline.analyze_feedback("")
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            default_pipeline.analyze_feedback("   \t  ")
        with pytest.raises(ValueError, match="cannot be None"):
            default_pipeline.analyze_feedback(None)
        with pytest.raises(TypeError, match="must be a string"):
            default_pipeline.analyze_feedback(9876)

    def test_tfidf_transform_only_behavior_with_priority(self, default_pipeline):
        """Condition 14: Existing TF-IDF transform-only behavior remains unchanged with priority."""
        vectorizer = default_pipeline._vectorizer
        vectorizer.fit = MagicMock(side_effect=RuntimeError("fit() called"))
        vectorizer.fit_transform = MagicMock(side_effect=RuntimeError("fit_transform() called"))

        try:
            result = default_pipeline.analyze_feedback("Fair examination guidelines.")
            assert "priority" in result
            assert vectorizer.fit.call_count == 0
            assert vectorizer.fit_transform.call_count == 0
        finally:
            del vectorizer.fit
            del vectorizer.fit_transform

    def test_calculate_from_intelligence_integration(self, default_pipeline):
        """Condition 15: calculate_from_intelligence integration directly matches pipeline output."""
        result = default_pipeline.analyze_feedback("The seminar was insightful.")
        direct_priority = default_pipeline._priority_scorer.calculate_from_intelligence(result)
        assert result["priority"] == direct_priority

