"""Deterministic Priority Scoring Engine for CampusVoice.

Evaluates student feedback intelligence (sentiment and category predictions
along with confidence metrics) to compute an explainable priority score (0–100),
priority tier (High, Medium, Low), and concise administrative reasoning.
"""

from typing import Any, Dict

VALID_SENTIMENTS = {"Negative", "Neutral", "Positive"}

PRIORITY_LEVEL_HIGH = "High"
PRIORITY_LEVEL_MEDIUM = "Medium"
PRIORITY_LEVEL_LOW = "Low"


class PriorityScorer:
    """Deterministic, rule-based priority scoring engine.

    Converts NLP/ML intelligence signals into an explainable administrative priority
    without modifying or retraining underlying machine learning models.
    """

    def __init__(self) -> None:
        """Initializes PriorityScorer instance."""
        pass

    @staticmethod
    def _validate_inputs(
        sentiment_name: Any,
        sentiment_confidence: Any,
        category_name: Any,
        category_confidence: Any,
    ) -> str:
        """Validates input types and values.

        Returns:
            Normalized title-case sentiment name.

        Raises:
            TypeError: If input types are invalid.
            ValueError: If input values are out of bounds or empty.
        """
        # 1. Validate sentiment_name
        if not isinstance(sentiment_name, str):
            raise TypeError(
                f"sentiment_name must be a string, got {type(sentiment_name).__name__}."
            )
        clean_sentiment = sentiment_name.strip().title()
        if clean_sentiment not in VALID_SENTIMENTS:
            raise ValueError(
                f"Invalid sentiment_name '{sentiment_name}'. Must be one of: {sorted(VALID_SENTIMENTS)}."
            )

        # 2. Validate sentiment_confidence
        if isinstance(sentiment_confidence, bool) or not isinstance(
            sentiment_confidence, (int, float)
        ):
            raise TypeError(
                f"sentiment_confidence must be numeric (float/int), got {type(sentiment_confidence).__name__}."
            )
        if sentiment_confidence < 0.0 or sentiment_confidence > 1.0:
            raise ValueError(
                f"sentiment_confidence must be between 0.0 and 1.0, got {sentiment_confidence}."
            )

        # 3. Validate category_name
        if not isinstance(category_name, str):
            raise TypeError(
                f"category_name must be a string, got {type(category_name).__name__}."
            )
        if not category_name.strip():
            raise ValueError("category_name cannot be empty or whitespace-only.")

        # 4. Validate category_confidence
        if isinstance(category_confidence, bool) or not isinstance(
            category_confidence, (int, float)
        ):
            raise TypeError(
                f"category_confidence must be numeric (float/int), got {type(category_confidence).__name__}."
            )
        if category_confidence < 0.0 or category_confidence > 1.0:
            raise ValueError(
                f"category_confidence must be between 0.0 and 1.0, got {category_confidence}."
            )

        return clean_sentiment

    def calculate(
        self,
        sentiment_name: str,
        sentiment_confidence: float,
        category_name: str,
        category_confidence: float,
    ) -> Dict[str, Any]:
        """Calculates deterministic priority score, tier, and explanation.

        Args:
            sentiment_name: Sentiment class ('Negative', 'Neutral', or 'Positive').
            sentiment_confidence: Sentiment model confidence score in [0.0, 1.0].
            category_name: Identified feedback category.
            category_confidence: Category model confidence score in [0.0, 1.0].

        Returns:
            Dict[str, Any]:
                - score (int): Priority score clamped between 0 and 100.
                - level (str): 'High', 'Medium', or 'Low'.
                - reason (str): Human-readable explanation.
        """
        sentiment = self._validate_inputs(
            sentiment_name=sentiment_name,
            sentiment_confidence=sentiment_confidence,
            category_name=category_name,
            category_confidence=category_confidence,
        )

        sent_conf = float(sentiment_confidence)
        cat_conf = float(category_confidence)

        # --- 1. Primary Signal: Sentiment Base Score ---
        if sentiment == "Negative":
            if sent_conf >= 0.70:
                base_score = 80
            elif sent_conf >= 0.50:
                base_score = 65
            else:
                base_score = 50
        elif sentiment == "Neutral":
            if sent_conf >= 0.70:
                base_score = 30
            elif sent_conf >= 0.50:
                base_score = 25
            else:
                base_score = 20
        else:  # Positive
            if sent_conf >= 0.70:
                base_score = 10
            elif sent_conf >= 0.50:
                base_score = 5
            else:
                base_score = 0

        # --- 2. Secondary Signal: Category Confidence Adjustment ---
        if cat_conf >= 0.70:
            category_adjustment = 10
        elif cat_conf >= 0.50:
            category_adjustment = 5
        else:
            category_adjustment = 0

        # --- 3. Compute and Clamp Total Score ---
        raw_score = base_score + category_adjustment
        final_score = max(0, min(100, raw_score))

        # --- 4. Resolve Priority Level ---
        if final_score >= 70:
            level = PRIORITY_LEVEL_HIGH
        elif final_score >= 40:
            level = PRIORITY_LEVEL_MEDIUM
        else:
            level = PRIORITY_LEVEL_LOW

        # --- 5. Generate Human-Readable Reason ---
        if sentiment == "Negative":
            if sent_conf >= 0.70:
                if cat_conf >= 0.70:
                    reason = "Negative sentiment with high confidence and clearly identified feedback category."
                else:
                    reason = "Negative sentiment detected with high confidence."
            elif sent_conf >= 0.50:
                reason = "Negative sentiment detected with moderate confidence."
            else:
                reason = "Negative sentiment detected with low confidence."
        elif sentiment == "Neutral":
            reason = "Neutral feedback with limited urgency based on sentiment."
        else:  # Positive
            reason = "Positive feedback indicates low immediate action priority."

        return {
            "score": int(final_score),
            "level": level,
            "reason": reason,
        }

    def calculate_from_intelligence(
        self,
        intelligence_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convenience method to calculate priority directly from Step 7 output.

        Args:
            intelligence_output: Dictionary returned by FeedbackIntelligencePipeline.analyze_feedback().

        Returns:
            Dict[str, Any]: Priority score, level, and reason dictionary.
        """
        if not isinstance(intelligence_output, dict):
            raise TypeError("intelligence_output must be a dictionary.")

        sentiment_dict = intelligence_output.get("sentiment", {})
        category_dict = intelligence_output.get("category", {})

        sentiment_name = sentiment_dict.get("name")
        sentiment_confidence = sentiment_dict.get("confidence")
        category_name = category_dict.get("name")
        category_confidence = category_dict.get("confidence")

        return self.calculate(
            sentiment_name=sentiment_name,
            sentiment_confidence=sentiment_confidence,
            category_name=category_name,
            category_confidence=category_confidence,
        )
