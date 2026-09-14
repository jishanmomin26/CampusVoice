"""Comprehensive Unit and Integration Tests for Feedback Statistics API (Step 9.5).

Validates:
  1. Empty database yields all zero counts and empty categories dictionary
  2. Legacy records with NULL analysis fields are counted in total and unclassified
  3. Legacy records do not contaminate positive/neutral/negative or high/medium/low
  4. Analyzed records increment positive, neutral, negative, and priority counts accurately
  5. Category counts aggregate dynamically without hardcoding to specific category names
  6. Case normalization handles mixed case sentiment and priority correctly
  7. Dynamic behavior: new feedback insertion immediately updates statistics
  8. GET /api/v1/feedback/stats returns HTTP 200 with complete validated schema
  9. Existing GET /api/v1/feedback remains functional alongside GET /stats
  10. Database error safely returns HTTP 500 without leaking stack traces or internal details
"""

from pathlib import Path
import sys
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.feedback import Feedback
from app.services.feedback_stats_service import get_feedback_statistics


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def in_memory_db():
    """In-memory SQLite database session fixture for isolated feedback DB testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestFeedbackStatisticsServiceLogic:
    """Validates aggregation logic and counting semantics at the service layer."""

    def test_empty_database_returns_zero_counts(self, in_memory_db):
        """Condition 1: An empty database yields zeroes for all counters and empty categories."""
        stats = get_feedback_statistics(in_memory_db)

        assert stats["total_feedback"] == 0
        assert stats["analyzed_feedback"] == 0
        assert stats["unclassified_feedback"] == 0
        assert stats["sentiment"] == {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "unclassified": 0,
        }
        assert stats["priority"] == {
            "high": 0,
            "medium": 0,
            "low": 0,
            "unclassified": 0,
        }
        assert stats["categories"] == {}

    def test_legacy_unclassified_records_handled_accurately(self, in_memory_db):
        """Condition 2 & 3: Legacy records with NULL analysis values are counted as unclassified only."""
        # Insert 3 legacy records with NULL analysis fields
        in_memory_db.add_all([
            Feedback(department="CS", semester="Sem 1", feedback_text="Lecture room AC broken."),
            Feedback(department="IT", semester="Sem 3", feedback_text="Need more lab hours."),
            Feedback(department="Mech", semester="Sem 5", feedback_text="Workshop tools missing."),
        ])
        in_memory_db.commit()

        stats = get_feedback_statistics(in_memory_db)

        assert stats["total_feedback"] == 3
        assert stats["analyzed_feedback"] == 0
        assert stats["unclassified_feedback"] == 3
        assert stats["sentiment"]["unclassified"] == 3
        assert stats["sentiment"]["positive"] == 0
        assert stats["sentiment"]["negative"] == 0
        assert stats["sentiment"]["neutral"] == 0
        assert stats["priority"]["unclassified"] == 3
        assert stats["priority"]["high"] == 0
        assert stats["priority"]["medium"] == 0
        assert stats["priority"]["low"] == 0
        assert stats["categories"] == {}

    def test_analyzed_records_aggregate_accurately(self, in_memory_db):
        """Condition 4: Analyzed records increment positive, neutral, negative, and priority counts."""
        in_memory_db.add_all([
            Feedback(
                feedback_text="Great course!",
                clean_text="great course",
                sentiment_name="positive",
                sentiment_confidence=0.88,
                category_name="Course Content",
                priority_level="Low",
                priority_score=10,
            ),
            Feedback(
                feedback_text="Average pace.",
                clean_text="average pace",
                sentiment_name="neutral",
                sentiment_confidence=0.72,
                category_name="Teaching",
                priority_level="Low",
                priority_score=20,
            ),
            Feedback(
                feedback_text="Faculty is very rude.",
                clean_text="faculty rude",
                sentiment_name="negative",
                sentiment_confidence=0.91,
                category_name="Teaching",
                priority_level="High",
                priority_score=85,
            ),
        ])
        in_memory_db.commit()

        stats = get_feedback_statistics(in_memory_db)

        assert stats["total_feedback"] == 3
        assert stats["analyzed_feedback"] == 3
        assert stats["unclassified_feedback"] == 0
        assert stats["sentiment"]["positive"] == 1
        assert stats["sentiment"]["neutral"] == 1
        assert stats["sentiment"]["negative"] == 1
        assert stats["sentiment"]["unclassified"] == 0
        assert stats["priority"]["high"] == 1
        assert stats["priority"]["medium"] == 0
        assert stats["priority"]["low"] == 2
        assert stats["priority"]["unclassified"] == 0
        assert stats["categories"] == {
            "Teaching": 2,
            "Course Content": 1,
        }

    def test_dynamic_categories_and_no_hardcoding(self, in_memory_db):
        """Condition 5: Custom and novel category names appear dynamically in the response."""
        in_memory_db.add_all([
            Feedback(
                feedback_text="Cafeteria food is cold.",
                sentiment_name="negative",
                category_name="Cafeteria & Food Services",
                priority_level="Medium",
            ),
            Feedback(
                feedback_text="Hostel water supply is irregular.",
                sentiment_name="negative",
                category_name="Hostel Facilities",
                priority_level="High",
            ),
        ])
        in_memory_db.commit()

        stats = get_feedback_statistics(in_memory_db)

        assert "Cafeteria & Food Services" in stats["categories"]
        assert stats["categories"]["Cafeteria & Food Services"] == 1
        assert "Hostel Facilities" in stats["categories"]
        assert stats["categories"]["Hostel Facilities"] == 1

    def test_case_normalization(self, in_memory_db):
        """Condition 6: Mixed case sentiment and priority entries are normalized consistently."""
        in_memory_db.add_all([
            Feedback(
                feedback_text="Text 1",
                sentiment_name="NEGATIVE",
                priority_level="HIGH",
                category_name="Teaching",
            ),
            Feedback(
                feedback_text="Text 2",
                sentiment_name="Negative",
                priority_level="High",
                category_name="Teaching",
            ),
            Feedback(
                feedback_text="Text 3",
                sentiment_name="negative",
                priority_level="high",
                category_name="Teaching",
            ),
        ])
        in_memory_db.commit()

        stats = get_feedback_statistics(in_memory_db)

        assert stats["total_feedback"] == 3
        assert stats["sentiment"]["negative"] == 3
        assert stats["priority"]["high"] == 3
        assert stats["categories"]["Teaching"] == 3

    def test_dynamic_updates_upon_new_record_insertion(self, in_memory_db):
        """Condition 7: Inserting additional records immediately updates aggregate counts."""
        rec1 = Feedback(
            feedback_text="First item",
            sentiment_name="positive",
            priority_level="Low",
            category_name="Library Facilities",
        )
        in_memory_db.add(rec1)
        in_memory_db.commit()

        stats1 = get_feedback_statistics(in_memory_db)
        assert stats1["total_feedback"] == 1
        assert stats1["sentiment"]["positive"] == 1

        rec2 = Feedback(
            feedback_text="Second item",
            sentiment_name="negative",
            priority_level="Medium",
            category_name="Teaching",
        )
        in_memory_db.add(rec2)
        in_memory_db.commit()

        stats2 = get_feedback_statistics(in_memory_db)
        assert stats2["total_feedback"] == 2
        assert stats2["sentiment"]["positive"] == 1
        assert stats2["sentiment"]["negative"] == 1
        assert stats2["priority"]["medium"] == 1
        assert stats2["categories"]["Teaching"] == 1


class TestFeedbackStatisticsAPIEndpoint:
    """Validates HTTP contract, response schema validation, and error handling."""

    def test_get_feedback_stats_returns_200_and_valid_schema(self, client, in_memory_db):
        """Condition 8: GET /api/v1/feedback/stats returns HTTP 200 with complete valid schema."""
        # Seed test data: 2 legacy and 2 analyzed
        in_memory_db.add_all([
            Feedback(department="CS", semester="Sem 2", feedback_text="Old legacy record 1"),
            Feedback(department="IT", semester="Sem 4", feedback_text="Old legacy record 2"),
            Feedback(
                feedback_text="The professor is very helpful and explains concepts clearly.",
                clean_text="professor helpful explain concept clear",
                sentiment_name="positive",
                sentiment_confidence=0.75,
                category_name="Teaching",
                priority_level="Low",
                priority_score=15,
            ),
            Feedback(
                feedback_text="The laboratory equipment is completely broken.",
                clean_text="laboratory equipment completely broken",
                sentiment_name="negative",
                sentiment_confidence=0.85,
                category_name="Lab Work",
                priority_level="High",
                priority_score=80,
            ),
        ])
        in_memory_db.commit()

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback/stats")
            assert response.status_code == 200
            data = response.json()

            assert data["total_feedback"] == 4
            assert data["analyzed_feedback"] == 2
            assert data["unclassified_feedback"] == 2
            assert data["sentiment"]["positive"] == 1
            assert data["sentiment"]["negative"] == 1
            assert data["sentiment"]["neutral"] == 0
            assert data["sentiment"]["unclassified"] == 2
            assert data["priority"]["high"] == 1
            assert data["priority"]["medium"] == 0
            assert data["priority"]["low"] == 1
            assert data["priority"]["unclassified"] == 2
            assert data["categories"] == {
                "Teaching": 1,
                "Lab Work": 1,
            }
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_existing_feedback_list_endpoint_still_functional(self, client, in_memory_db):
        """Condition 9: GET /api/v1/feedback still returns records without route collision."""
        in_memory_db.add(Feedback(department="CS", semester="Sem 1", feedback_text="Smoke test"))
        in_memory_db.commit()

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            list_res = client.get("/api/v1/feedback")
            assert list_res.status_code == 200
            assert isinstance(list_res.json(), list)
            assert len(list_res.json()) == 1

            stats_res = client.get("/api/v1/feedback/stats")
            assert stats_res.status_code == 200
            assert isinstance(stats_res.json(), dict)
            assert stats_res.json()["total_feedback"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_database_failure_returns_safe_500(self, client, in_memory_db):
        """Condition 10: Database exception returns safe HTTP 500 without leaking stack traces."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            with patch("app.api.v1.endpoints.feedback.get_feedback_statistics") as mock_stats:
                mock_stats.side_effect = SQLAlchemyError("Simulated raw database crash")
                response = client.get("/api/v1/feedback/stats")
                assert response.status_code == 500
                detail = response.json()["detail"]
                assert "internal database error" in detail.lower()
                assert "Simulated raw database crash" not in detail
        finally:
            app.dependency_overrides.pop(get_db, None)
