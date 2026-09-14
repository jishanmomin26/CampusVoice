"""CampusVoice Unified Feedback Intelligence Pipeline.

Combines Step 3 NLP preprocessing, Step 5 Sentiment Classification,
and Step 6 Category Classification into a single reusable inference pipeline.
"""

from ml.pipeline.feedback_intelligence import (
    FeedbackIntelligencePipeline,
    analyze_feedback,
)

__all__ = ["FeedbackIntelligencePipeline", "analyze_feedback"]
