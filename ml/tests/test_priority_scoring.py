"""Comprehensive Test Suite for the Priority Scoring Engine (Step 8.1).

Validates 21 distinct conditions:
  1. PriorityScorer initializes.
  2. High-confidence negative feedback produces High priority.
  3. Moderate-confidence negative feedback produces appropriate priority.
  4. Low-confidence negative feedback produces appropriate priority.
  5. High-confidence neutral feedback produces Low priority (when score < 40).
  6. High-confidence positive feedback produces Low priority.
  7. Category confidence >= 0.70 adds +10.
  8. Category confidence >= 0.50 adds +5.
  9. Category confidence < 0.50 adds no adjustment.
  10. Final score is clamped to 0–100.
  11. Exact 0.50 boundaries work.
  12. Exact 0.70 boundaries work.
  13. Exact 1.0 confidence works.
  14. Exact 0.0 confidence works.
  15. Invalid sentiment name is rejected.
  16. Invalid sentiment confidence is rejected.
  17. Invalid category confidence is rejected.
  18. Empty category name is rejected.
  19. Non-string sentiment is rejected.
  20. Repeated calculations produce identical results.
  21. Existing Step 7 functionality remains unaffected.
"""

from pathlib import Path
import sys
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

from ml.priority.priority_scoring import (
    PRIORITY_LEVEL_HIGH,
    PRIORITY_LEVEL_LOW,
    PRIORITY_LEVEL_MEDIUM,
    PriorityScorer,
)


@pytest.fixture
def scorer():
    """Initializes PriorityScorer instance."""
    return PriorityScorer()


class TestPriorityScorerInitialization:
    """Validates scorer initialization (Condition 1)."""

    def test_condition_1_scorer_initializes(self, scorer):
        """Condition 1: PriorityScorer initializes without error."""
        assert scorer is not None
        assert isinstance(scorer, PriorityScorer)


class TestSentimentDrivenScoringAndTiers:
    """Validates sentiment-driven priority tiers (Conditions 2-6)."""

    def test_condition_2_high_confidence_negative_produces_high_priority(self, scorer):
        """Condition 2: High-confidence negative feedback (sent_conf >= 0.70) yields High priority."""
        res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.85,
            category_name="Teaching",
            category_confidence=0.75,
        )
        # 80 base + 10 cat = 90
        assert res["score"] == 90
        assert res["level"] == PRIORITY_LEVEL_HIGH
        assert "Negative sentiment with high confidence" in res["reason"]

    def test_condition_3_moderate_confidence_negative_produces_appropriate_priority(self, scorer):
        """Condition 3: Moderate-confidence negative feedback (0.50 <= sent_conf < 0.70) produces expected priority."""
        # 65 base + 10 cat = 75 -> High
        res_high = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.60,
            category_name="Lab Work",
            category_confidence=0.75,
        )
        assert res_high["score"] == 75
        assert res_high["level"] == PRIORITY_LEVEL_HIGH

        # 65 base + 0 cat = 65 -> Medium
        res_med = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.55,
            category_name="Lab Work",
            category_confidence=0.40,
        )
        assert res_med["score"] == 65
        assert res_med["level"] == PRIORITY_LEVEL_MEDIUM

    def test_condition_4_low_confidence_negative_produces_appropriate_priority(self, scorer):
        """Condition 4: Low-confidence negative feedback (sent_conf < 0.50) produces Medium priority."""
        # 50 base + 5 cat = 55 -> Medium
        res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.45,
            category_name="Examination",
            category_confidence=0.55,
        )
        assert res["score"] == 55
        assert res["level"] == PRIORITY_LEVEL_MEDIUM

    def test_condition_5_high_confidence_neutral_produces_low_priority(self, scorer):
        """Condition 5: High-confidence neutral feedback (sent_conf >= 0.70) produces Low priority when score < 40."""
        # 30 base + 5 cat = 35 -> Low
        res = scorer.calculate(
            sentiment_name="Neutral",
            sentiment_confidence=0.80,
            category_name="Course Content",
            category_confidence=0.60,
        )
        assert res["score"] == 35
        assert res["level"] == PRIORITY_LEVEL_LOW
        assert "Neutral feedback" in res["reason"]

    def test_condition_6_high_confidence_positive_produces_low_priority(self, scorer):
        """Condition 6: High-confidence positive feedback produces Low priority."""
        # 10 base + 10 cat = 20 -> Low
        res = scorer.calculate(
            sentiment_name="Positive",
            sentiment_confidence=0.90,
            category_name="Library Facilities",
            category_confidence=0.80,
        )
        assert res["score"] == 20
        assert res["level"] == PRIORITY_LEVEL_LOW
        assert "Positive feedback" in res["reason"]


class TestCategoryConfidenceAdjustments:
    """Validates category confidence adjustment tiers (Conditions 7-9)."""

    def test_condition_7_category_confidence_high_adds_ten(self, scorer):
        """Condition 7: Category confidence >= 0.70 adds exactly +10."""
        # Neutral base 25 (0.55 conf) + 10 = 35
        res = scorer.calculate(
            sentiment_name="Neutral",
            sentiment_confidence=0.55,
            category_name="Teaching",
            category_confidence=0.70,
        )
        assert res["score"] == 35

    def test_condition_8_category_confidence_moderate_adds_five(self, scorer):
        """Condition 8: Category confidence >= 0.50 (and < 0.70) adds exactly +5."""
        # Neutral base 25 (0.55 conf) + 5 = 30
        res = scorer.calculate(
            sentiment_name="Neutral",
            sentiment_confidence=0.55,
            category_name="Teaching",
            category_confidence=0.50,
        )
        assert res["score"] == 30

    def test_condition_9_category_confidence_low_adds_zero(self, scorer):
        """Condition 9: Category confidence < 0.50 adds +0."""
        # Neutral base 25 (0.55 conf) + 0 = 25
        res = scorer.calculate(
            sentiment_name="Neutral",
            sentiment_confidence=0.55,
            category_name="Teaching",
            category_confidence=0.49,
        )
        assert res["score"] == 25


class TestClampingAndBoundaryValues:
    """Validates score clamping and exact threshold boundaries (Conditions 10-14)."""

    def test_condition_10_score_clamping(self, scorer):
        """Condition 10: Final score is clamped within [0, 100]."""
        # Minimum possible: Positive low-conf (0) + low cat (0) = 0
        min_res = scorer.calculate(
            sentiment_name="Positive",
            sentiment_confidence=0.10,
            category_name="Teaching",
            category_confidence=0.10,
        )
        assert min_res["score"] >= 0

        # Maximum possible: Negative high-conf (80) + high cat (10) = 90 (clamped <= 100)
        max_res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.99,
            category_name="Teaching",
            category_confidence=0.99,
        )
        assert max_res["score"] <= 100

    def test_condition_11_exact_half_boundaries(self, scorer):
        """Condition 11: Exact 0.50 boundaries activate the moderate tier."""
        # At sent_conf = 0.50, Negative base is 65 (not 50)
        # At cat_conf = 0.50, Category adjustment is +5 (not +0)
        res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.50,
            category_name="Lab Work",
            category_confidence=0.50,
        )
        assert res["score"] == 65 + 5  # 70 -> High
        assert res["level"] == PRIORITY_LEVEL_HIGH

    def test_condition_12_exact_seventy_boundaries(self, scorer):
        """Condition 12: Exact 0.70 boundaries activate the high tier."""
        # At sent_conf = 0.70, Negative base is 80 (not 65)
        # At cat_conf = 0.70, Category adjustment is +10 (not +5)
        res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=0.70,
            category_name="Lab Work",
            category_confidence=0.70,
        )
        assert res["score"] == 80 + 10  # 90 -> High
        assert res["level"] == PRIORITY_LEVEL_HIGH

    def test_condition_13_exact_one_confidence(self, scorer):
        """Condition 13: Exact 1.0 confidence works properly without overflow."""
        res = scorer.calculate(
            sentiment_name="Negative",
            sentiment_confidence=1.0,
            category_name="Examination",
            category_confidence=1.0,
        )
        assert res["score"] == 90
        assert res["level"] == PRIORITY_LEVEL_HIGH

    def test_condition_14_exact_zero_confidence(self, scorer):
        """Condition 14: Exact 0.0 confidence works properly without underflow."""
        res = scorer.calculate(
            sentiment_name="Positive",
            sentiment_confidence=0.0,
            category_name="Extracurricular",
            category_confidence=0.0,
        )
        assert res["score"] == 0
        assert res["level"] == PRIORITY_LEVEL_LOW


class TestInputValidationAndRejection:
    """Validates robust rejection of invalid arguments (Conditions 15-19)."""

    def test_condition_15_invalid_sentiment_name_rejected(self, scorer):
        """Condition 15: Invalid sentiment string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sentiment_name"):
            scorer.calculate(
                sentiment_name="Angry",
                sentiment_confidence=0.80,
                category_name="Teaching",
                category_confidence=0.80,
            )

    def test_condition_16_invalid_sentiment_confidence_rejected(self, scorer):
        """Condition 16: Out-of-bounds or non-numeric sentiment confidence raises error."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=1.5,
                category_name="Teaching",
                category_confidence=0.5,
            )

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=-0.1,
                category_name="Teaching",
                category_confidence=0.5,
            )

        with pytest.raises(TypeError):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence="high",
                category_name="Teaching",
                category_confidence=0.5,
            )

        with pytest.raises(TypeError):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=True,
                category_name="Teaching",
                category_confidence=0.5,
            )

    def test_condition_17_invalid_category_confidence_rejected(self, scorer):
        """Condition 17: Out-of-bounds or non-numeric category confidence raises error."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=0.8,
                category_name="Teaching",
                category_confidence=1.1,
            )

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=0.8,
                category_name="Teaching",
                category_confidence=-0.05,
            )

        with pytest.raises(TypeError):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=0.8,
                category_name="Teaching",
                category_confidence=None,
            )

    def test_condition_18_empty_category_name_rejected(self, scorer):
        """Condition 18: Empty or whitespace category name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=0.8,
                category_name="",
                category_confidence=0.5,
            )

        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            scorer.calculate(
                sentiment_name="Negative",
                sentiment_confidence=0.8,
                category_name="   \t\n  ",
                category_confidence=0.5,
            )

    def test_condition_19_non_string_sentiment_rejected(self, scorer):
        """Condition 19: Non-string sentiment raises TypeError."""
        with pytest.raises(TypeError, match="must be a string"):
            scorer.calculate(
                sentiment_name=123,
                sentiment_confidence=0.8,
                category_name="Teaching",
                category_confidence=0.5,
            )

        with pytest.raises(TypeError, match="must be a string"):
            scorer.calculate(
                sentiment_name=None,
                sentiment_confidence=0.8,
                category_name="Teaching",
                category_confidence=0.5,
            )


class TestDeterminismAndPipelineIntegration:
    """Validates determinism and seamless Step 7 integration (Conditions 20-21)."""

    def test_condition_20_repeated_calculations_produce_identical_results(self, scorer):
        """Condition 20: Deterministic scoring produces identical results across repeated runs."""
        args = {
            "sentiment_name": "Negative",
            "sentiment_confidence": 0.82,
            "category_name": "Teaching",
            "category_confidence": 0.76,
        }
        res1 = scorer.calculate(**args)
        res2 = scorer.calculate(**args)
        res3 = scorer.calculate(**args)

        assert res1 == res2 == res3
        assert res1["score"] == 90
        assert res1["level"] == PRIORITY_LEVEL_HIGH

    def test_condition_21_step7_intelligence_integration_unaffected(self, scorer):
        """Condition 21: calculate_from_intelligence correctly consumes Step 7 output schema."""
        from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline

        pipeline = FeedbackIntelligencePipeline()
        intelligence = pipeline.analyze_feedback(
            "The laboratory computers are very old and outdated."
        )

        # Confirm intelligence dictionary has expected keys
        assert "sentiment" in intelligence
        assert "category" in intelligence

        priority_res = scorer.calculate_from_intelligence(intelligence)

        assert "score" in priority_res
        assert "level" in priority_res
        assert "reason" in priority_res
        assert 0 <= priority_res["score"] <= 100
        assert priority_res["level"] in {
            PRIORITY_LEVEL_HIGH,
            PRIORITY_LEVEL_MEDIUM,
            PRIORITY_LEVEL_LOW,
        }
        assert isinstance(priority_res["reason"], str)
