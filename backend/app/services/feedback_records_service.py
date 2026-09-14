"""Feedback Records Service for Paginated and Filtered Record Retrieval."""

import logging
import math
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback

logger = logging.getLogger(__name__)

# Canonical allowed values for sentiment and priority filters
ALLOWED_SENTIMENTS = {"positive", "neutral", "negative"}
ALLOWED_PRIORITIES = {"high", "medium", "low"}


def get_feedback_records(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves paginated, filtered feedback records directly from PostgreSQL.

    Performs all filtering, counting, ordering, and pagination at the database level
    using SQLAlchemy to prevent loading unnecessary records into Python memory.

    Args:
        db: Active SQLAlchemy database session.
        page: Current page number (1-indexed, default: 1).
        page_size: Maximum number of records per page (default: 10).
        search: Optional case-insensitive substring search for feedback_text.
        sentiment: Optional sentiment filter ('positive', 'neutral', 'negative').
        category: Optional category filter (dynamic, case-insensitive).
        priority: Optional priority tier filter ('high', 'medium', 'low').

    Returns:
        Dict[str, Any]: Formatted data dictionary matching FeedbackRecordsResponse schema:
            - items: List of Feedback ORM instances for the requested page.
            - total: Total count of records matching all active filters.
            - page: Current page number.
            - page_size: Items per page.
            - total_pages: Total number of pages (0 if total is 0).

    Raises:
        HTTPException: 422 Unprocessable Entity if sentiment or priority values are invalid.
    """
    conditions = []

    # 1. Validate and apply sentiment filter
    if sentiment is not None:
        sentiment_clean = sentiment.strip()
        if sentiment_clean:
            sentiment_normalized = sentiment_clean.lower()
            if sentiment_normalized not in ALLOWED_SENTIMENTS:
                logger.warning("Invalid sentiment filter requested: %s", sentiment)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid sentiment filter: '{sentiment}'. "
                        f"Allowed values are: {', '.join(sorted(ALLOWED_SENTIMENTS))}."
                    ),
                )
            # NULL sentiment_name rows represent unclassified feedback and must NOT match
            conditions.append(
                Feedback.sentiment_name.is_not(None)
            )
            conditions.append(
                func.lower(Feedback.sentiment_name) == sentiment_normalized
            )

    # 2. Validate and apply priority filter
    if priority is not None:
        priority_clean = priority.strip()
        if priority_clean:
            priority_normalized = priority_clean.lower()
            if priority_normalized not in ALLOWED_PRIORITIES:
                logger.warning("Invalid priority filter requested: %s", priority)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid priority filter: '{priority}'. "
                        f"Allowed values are: {', '.join(sorted(ALLOWED_PRIORITIES))}."
                    ),
                )
            # NULL priority_level rows represent unclassified feedback and must NOT match
            conditions.append(
                Feedback.priority_level.is_not(None)
            )
            conditions.append(
                func.lower(Feedback.priority_level) == priority_normalized
            )

    # 3. Apply category filter (dynamic, case-insensitive)
    if category is not None:
        category_clean = category.strip()
        if category_clean:
            conditions.append(
                Feedback.category_name.is_not(None)
            )
            conditions.append(
                func.lower(Feedback.category_name) == category_clean.lower()
            )

    # 4. Apply search filter (case-insensitive substring on feedback_text)
    if search is not None:
        search_clean = search.strip()
        if search_clean:
            conditions.append(
                Feedback.feedback_text.ilike(f"%{search_clean}%")
            )

    # 5. Execute count query matching all active filter conditions
    count_statement = select(func.count(Feedback.id))
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = db.scalar(count_statement) or 0

    # 6. Calculate total pages
    if total == 0:
        total_pages = 0
    else:
        total_pages = math.ceil(total / page_size)

    # 7. Apply deterministic ordering and database pagination
    offset = (page - 1) * page_size
    query_statement = select(Feedback)
    if conditions:
        query_statement = query_statement.where(*conditions)

    # Order newest first; break ties with descending ID for deterministic pagination
    query_statement = (
        query_statement.order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .offset(offset)
        .limit(page_size)
    )

    items: List[Feedback] = list(db.scalars(query_statement).all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
