"""Feedback Statistics Service for Admin Dashboard."""

import logging
from typing import Any, Dict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback

logger = logging.getLogger(__name__)


def get_feedback_statistics(db: Session) -> Dict[str, Any]:
    """Calculates dynamic database-backed aggregate feedback statistics.

    Uses SQL database-side aggregation (func.count and group_by) to compute
    total feedback volume, analyzed vs. unclassified volumes, normalized
    sentiment breakdown, normalized priority breakdown, and dynamic category
    distribution without loading feedback records or embeddings into Python memory.

    Args:
        db: Active SQLAlchemy database session.

    Returns:
        Dict[str, Any]: Dictionary formatted according to FeedbackStatsResponse.
    """
    # 1. Total feedback count across all database records
    total_feedback = db.scalar(select(func.count(Feedback.id))) or 0

    # 2. Analyzed feedback count (defined by sentiment_name IS NOT NULL)
    analyzed_feedback = (
        db.scalar(
            select(func.count(Feedback.id)).where(Feedback.sentiment_name.is_not(None))
        )
        or 0
    )

    # 3. Unclassified feedback count (defined by sentiment_name IS NULL)
    unclassified_feedback = total_feedback - analyzed_feedback

    # 4. Aggregate sentiment counts with case normalization
    sentiment_counts = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "unclassified": 0,
    }
    sentiment_stmt = (
        select(func.lower(Feedback.sentiment_name), func.count(Feedback.id))
        .group_by(func.lower(Feedback.sentiment_name))
    )
    for raw_label, count in db.execute(sentiment_stmt).all():
        if raw_label is None:
            sentiment_counts["unclassified"] += count
        else:
            normalized_label = raw_label.strip()
            if normalized_label in sentiment_counts:
                sentiment_counts[normalized_label] += count
            else:
                sentiment_counts["unclassified"] += count

    # Guarantee mathematical consistency for unclassified count
    if sentiment_counts["unclassified"] != unclassified_feedback:
        sentiment_counts["unclassified"] = unclassified_feedback

    # 5. Aggregate priority counts with case normalization
    priority_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unclassified": 0,
    }
    priority_stmt = (
        select(func.lower(Feedback.priority_level), func.count(Feedback.id))
        .group_by(func.lower(Feedback.priority_level))
    )
    for raw_tier, count in db.execute(priority_stmt).all():
        if raw_tier is None:
            priority_counts["unclassified"] += count
        else:
            normalized_tier = raw_tier.strip()
            if normalized_tier in priority_counts:
                priority_counts[normalized_tier] += count
            else:
                priority_counts["unclassified"] += count

    # 6. Aggregate non-null category counts dynamically (no hardcoded category list)
    categories_dict: Dict[str, int] = {}
    category_stmt = (
        select(Feedback.category_name, func.count(Feedback.id))
        .where(Feedback.category_name.is_not(None))
        .group_by(Feedback.category_name)
        .order_by(func.count(Feedback.id).desc(), Feedback.category_name.asc())
    )
    for cat_name, count in db.execute(category_stmt).all():
        if cat_name and cat_name.strip():
            categories_dict[cat_name.strip()] = count

    return {
        "total_feedback": total_feedback,
        "analyzed_feedback": analyzed_feedback,
        "unclassified_feedback": unclassified_feedback,
        "sentiment": sentiment_counts,
        "priority": priority_counts,
        "categories": categories_dict,
    }
