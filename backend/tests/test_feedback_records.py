"""Comprehensive Unit and Integration Tests for Feedback Records API (Step 9.8).

Validates:
  1. Empty database yields empty items, total 0, and total_pages 0
  2. Default pagination (page=1, page_size=10)
  3. Custom page size (e.g. page_size=2)
  4. Multiple pages pagination (e.g. page=2)
  5. Search filter matches keyword in feedback_text
  6. Case-insensitive search filter
  7. Sentiment filter (positive, neutral, negative)
  8. Case-insensitive sentiment filter
  9. Category filter (dynamic category support)
  10. Case-insensitive category filter
  11. Priority filter (high, medium, low)
  12. Case-insensitive priority filter
  13. Combined filters (search + sentiment + category + priority + pagination)
  14. Invalid sentiment filter returns HTTP 422
  15. Invalid priority filter returns HTTP 422
  16. Empty filter result returns items=[], total=0, total_pages=0 without error
  17. NULL/unclassified fields serialized correctly and excluded from sentiment/priority filters
  18. Newest-first ordering (created_at DESC)
  19. Stable deterministic ordering with equal timestamps (id DESC)
  20. Total count strictly reflects active filters
  21. Total pages calculation: ceil(total / page_size), total=0 -> 0
  22. Complete API response schema validation
  23. Existing feedback endpoints regression (GET /feedback, POST /feedback, POST /analyze-and-save, GET /stats)
  24. Database error handling returns HTTP 500
  25. Out-of-range page returns empty items list with valid pagination metadata
  26. Invalid pagination parameters (page < 1, page_size < 1, page_size > 100) return HTTP 422
"""

from datetime import datetime, timezone, timedelta
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
from app.services.feedback_records_service import get_feedback_records


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


def _seed_sample_records(db):
    """Helper to populate diverse sample feedback records for testing."""
    now = datetime.now(timezone.utc)
    records = [
        # ID 1: Legacy unclassified record
        Feedback(
            department="Computer Science",
            semester="Semester 1",
            feedback_text="Old legacy comment before AI integration.",
            created_at=now - timedelta(days=10),
        ),
        # ID 2: Teaching, Negative, High
        Feedback(
            department="Computer Science",
            semester="Semester 3",
            feedback_text="Professor arrives late to lectures and does not explain algorithms clearly.",
            clean_text="professor arrive late lecture not explain algorithm clearly",
            sentiment_label=-1,
            sentiment_name="negative",
            sentiment_confidence=0.88,
            category_name="Teaching",
            category_confidence=0.85,
            priority_score=85,
            priority_level="High",
            priority_reason="High confidence negative sentiment.",
            created_at=now - timedelta(days=5),
        ),
        # ID 3: Teaching, Positive, Low
        Feedback(
            department="Mathematics",
            semester="Semester 2",
            feedback_text="Great lecture presentation by the calculus instructor!",
            clean_text="great lecture presentation calculus instructor",
            sentiment_label=1,
            sentiment_name="positive",
            sentiment_confidence=0.92,
            category_name="Teaching",
            category_confidence=0.90,
            priority_score=10,
            priority_level="Low",
            priority_reason="Positive feedback.",
            created_at=now - timedelta(days=4),
        ),
        # ID 4: Lab Work, Negative, High
        Feedback(
            department="Chemistry",
            semester="Semester 4",
            feedback_text="Chemistry lab glassware is broken and safety equipment is missing.",
            clean_text="chemistry lab glassware break safety equipment miss",
            sentiment_label=-1,
            sentiment_name="negative",
            sentiment_confidence=0.91,
            category_name="Lab Work",
            category_confidence=0.89,
            priority_score=90,
            priority_level="High",
            priority_reason="Urgent laboratory safety concern.",
            created_at=now - timedelta(days=3),
        ),
        # ID 5: Lab Work, Neutral, Medium
        Feedback(
            department="Physics",
            semester="Semester 4",
            feedback_text="Lab computers are usable but the operating system needs an update.",
            clean_text="lab computer usable operating system need update",
            sentiment_label=0,
            sentiment_name="neutral",
            sentiment_confidence=0.65,
            category_name="Lab Work",
            category_confidence=0.75,
            priority_score=45,
            priority_level="Medium",
            priority_reason="Moderate priority maintenance note.",
            created_at=now - timedelta(days=2),
        ),
        # ID 6: Library Facilities, Positive, Low
        Feedback(
            department="Library",
            semester="Semester 6",
            feedback_text="The campus library quiet study floor is very peaceful and well kept.",
            clean_text="campus library quiet study floor peaceful well keep",
            sentiment_label=1,
            sentiment_name="positive",
            sentiment_confidence=0.85,
            category_name="Library Facilities",
            category_confidence=0.92,
            priority_score=5,
            priority_level="Low",
            priority_reason="Positive feedback.",
            created_at=now - timedelta(days=1),
        ),
    ]
    db.add_all(records)
    db.commit()


class TestFeedbackRecordsServiceLogic:
    """Validates service-layer query building, filtering, ordering, and pagination."""

    def test_condition_1_empty_database(self, in_memory_db):
        """Scenario 1: Empty database returns empty items, total 0, and total_pages 0."""
        result = get_feedback_records(in_memory_db, page=1, page_size=10)
        assert result["items"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total_pages"] == 0

    def test_condition_2_default_pagination(self, in_memory_db):
        """Scenario 2: Default pagination with 6 records returns all 6 records on page 1."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, page=1, page_size=10)
        assert len(result["items"]) == 6
        assert result["total"] == 6
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total_pages"] == 1

    def test_condition_3_custom_page_size(self, in_memory_db):
        """Scenario 3: Custom page_size=2 returns exactly 2 records and total_pages=3."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total"] == 6
        assert result["total_pages"] == 3

    def test_condition_4_multiple_pages(self, in_memory_db):
        """Scenario 4: Querying page 2 returns distinct next records."""
        _seed_sample_records(in_memory_db)
        page1 = get_feedback_records(in_memory_db, page=1, page_size=2)
        page2 = get_feedback_records(in_memory_db, page=2, page_size=2)
        page1_ids = [item.id for item in page1["items"]]
        page2_ids = [item.id for item in page2["items"]]

        assert len(page2["items"]) == 2
        assert set(page1_ids).isdisjoint(set(page2_ids))

    def test_condition_5_search_filter(self, in_memory_db):
        """Scenario 5: Search parameter filters records by feedback_text substring."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, search="glassware")
        assert result["total"] == 1
        assert "glassware" in result["items"][0].feedback_text

    def test_condition_6_case_insensitive_search(self, in_memory_db):
        """Scenario 6: Search is case-insensitive."""
        _seed_sample_records(in_memory_db)
        result_lower = get_feedback_records(in_memory_db, search="professor")
        result_upper = get_feedback_records(in_memory_db, search="PROFESSOR")
        result_mixed = get_feedback_records(in_memory_db, search="ProFeSSor")

        assert result_lower["total"] == 1
        assert result_upper["total"] == 1
        assert result_mixed["total"] == 1
        assert result_lower["items"][0].id == result_upper["items"][0].id

    def test_condition_7_sentiment_filter(self, in_memory_db):
        """Scenario 7: Sentiment filter returns only matching records."""
        _seed_sample_records(in_memory_db)
        neg_result = get_feedback_records(in_memory_db, sentiment="negative")
        pos_result = get_feedback_records(in_memory_db, sentiment="positive")
        neu_result = get_feedback_records(in_memory_db, sentiment="neutral")

        assert neg_result["total"] == 2
        assert all(item.sentiment_name == "negative" for item in neg_result["items"])
        assert pos_result["total"] == 2
        assert all(item.sentiment_name == "positive" for item in pos_result["items"])
        assert neu_result["total"] == 1
        assert all(item.sentiment_name == "neutral" for item in neu_result["items"])

    def test_condition_8_case_insensitive_sentiment_filter(self, in_memory_db):
        """Scenario 8: Sentiment filter accepts any case."""
        _seed_sample_records(in_memory_db)
        res1 = get_feedback_records(in_memory_db, sentiment="negative")
        res2 = get_feedback_records(in_memory_db, sentiment="Negative")
        res3 = get_feedback_records(in_memory_db, sentiment="NEGATIVE")

        assert res1["total"] == 2
        assert res2["total"] == 2
        assert res3["total"] == 2

    def test_condition_9_category_filter(self, in_memory_db):
        """Scenario 9: Category filter dynamically matches category_name."""
        _seed_sample_records(in_memory_db)
        teaching_res = get_feedback_records(in_memory_db, category="Teaching")
        lab_res = get_feedback_records(in_memory_db, category="Lab Work")

        assert teaching_res["total"] == 2
        assert all(item.category_name == "Teaching" for item in teaching_res["items"])
        assert lab_res["total"] == 2
        assert all(item.category_name == "Lab Work" for item in lab_res["items"])

    def test_condition_10_case_insensitive_category_filter(self, in_memory_db):
        """Scenario 10: Category filter comparison is case-insensitive."""
        _seed_sample_records(in_memory_db)
        res1 = get_feedback_records(in_memory_db, category="teaching")
        res2 = get_feedback_records(in_memory_db, category="TEACHING")

        assert res1["total"] == 2
        assert res2["total"] == 2

    def test_condition_11_priority_filter(self, in_memory_db):
        """Scenario 11: Priority filter matches priority tier."""
        _seed_sample_records(in_memory_db)
        high_res = get_feedback_records(in_memory_db, priority="high")
        med_res = get_feedback_records(in_memory_db, priority="medium")
        low_res = get_feedback_records(in_memory_db, priority="low")

        assert high_res["total"] == 2
        assert all(item.priority_level == "High" for item in high_res["items"])
        assert med_res["total"] == 1
        assert all(item.priority_level == "Medium" for item in med_res["items"])
        assert low_res["total"] == 2
        assert all(item.priority_level == "Low" for item in low_res["items"])

    def test_condition_12_case_insensitive_priority_filter(self, in_memory_db):
        """Scenario 12: Priority filter is case-insensitive."""
        _seed_sample_records(in_memory_db)
        res1 = get_feedback_records(in_memory_db, priority="high")
        res2 = get_feedback_records(in_memory_db, priority="High")
        res3 = get_feedback_records(in_memory_db, priority="HIGH")

        assert res1["total"] == 2
        assert res2["total"] == 2
        assert res3["total"] == 2

    def test_condition_13_combined_filters(self, in_memory_db):
        """Scenario 13: Multiple filters operate simultaneously via SQL AND conditions."""
        _seed_sample_records(in_memory_db)
        # Search "equipment" + category "Lab Work" + sentiment "negative" + priority "high"
        result = get_feedback_records(
            in_memory_db,
            search="equipment",
            category="Lab Work",
            sentiment="negative",
            priority="high",
        )
        assert result["total"] == 1
        record = result["items"][0]
        assert "equipment" in record.feedback_text
        assert record.category_name == "Lab Work"
        assert record.sentiment_name == "negative"
        assert record.priority_level == "High"

    def test_condition_14_invalid_sentiment_raises_422(self, in_memory_db):
        """Scenario 14: Invalid sentiment filter value raises HTTP 422."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_feedback_records(in_memory_db, sentiment="angry")
        assert exc_info.value.status_code == 422
        assert "Invalid sentiment filter" in exc_info.value.detail

    def test_condition_15_invalid_priority_raises_422(self, in_memory_db):
        """Scenario 15: Invalid priority filter value raises HTTP 422."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_feedback_records(in_memory_db, priority="critical")
        assert exc_info.value.status_code == 422
        assert "Invalid priority filter" in exc_info.value.detail

    def test_condition_16_empty_filter_result_returns_empty_items(self, in_memory_db):
        """Scenario 16: Category that does not exist returns empty items without error."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, category="NonExistentCategory")
        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 0

    def test_condition_17_null_unclassified_legacy_records_not_matched(self, in_memory_db):
        """Scenario 17: Legacy records with NULL sentiment/priority are NOT matched by sentiment/priority filters."""
        _seed_sample_records(in_memory_db)
        # 6 total records, 1 has sentiment=NULL, priority=NULL
        neg_count = get_feedback_records(in_memory_db, sentiment="negative")["total"]
        pos_count = get_feedback_records(in_memory_db, sentiment="positive")["total"]
        neu_count = get_feedback_records(in_memory_db, sentiment="neutral")["total"]
        assert neg_count + pos_count + neu_count == 5  # Legacy record excluded

        # But legacy record is returned when no sentiment filter is applied
        all_records = get_feedback_records(in_memory_db, page_size=100)
        legacy_item = next(item for item in all_records["items"] if item.id == 1)
        assert legacy_item.sentiment_name is None
        assert legacy_item.category_name is None
        assert legacy_item.priority_level is None

    def test_condition_18_newest_first_ordering(self, in_memory_db):
        """Scenario 18: Records are ordered by created_at DESC (newest first)."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, page_size=10)
        created_dates = [item.created_at for item in result["items"]]
        assert created_dates == sorted(created_dates, reverse=True)

    def test_condition_19_stable_ordering_with_equal_timestamps(self, in_memory_db):
        """Scenario 19: Equal timestamps are deterministically ordered by id DESC."""
        same_time = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
        in_memory_db.add_all([
            Feedback(department="CS", feedback_text="First", created_at=same_time),
            Feedback(department="CS", feedback_text="Second", created_at=same_time),
            Feedback(department="CS", feedback_text="Third", created_at=same_time),
        ])
        in_memory_db.commit()

        result = get_feedback_records(in_memory_db, page_size=10)
        ids = [item.id for item in result["items"]]
        # Higher IDs created later should appear first
        assert ids == sorted(ids, reverse=True)

    def test_condition_20_total_count_reflects_active_filters(self, in_memory_db):
        """Scenario 20: Total count reflects the filtered dataset, not total DB rows."""
        _seed_sample_records(in_memory_db)
        total_db = get_feedback_records(in_memory_db)["total"]
        assert total_db == 6

        filtered = get_feedback_records(in_memory_db, sentiment="negative")
        assert filtered["total"] == 2

    def test_condition_21_total_pages_calculation(self, in_memory_db):
        """Scenario 21: Total pages is calculated as ceil(total / page_size)."""
        _seed_sample_records(in_memory_db)
        # 6 records
        assert get_feedback_records(in_memory_db, page_size=6)["total_pages"] == 1
        assert get_feedback_records(in_memory_db, page_size=5)["total_pages"] == 2
        assert get_feedback_records(in_memory_db, page_size=2)["total_pages"] == 3
        assert get_feedback_records(in_memory_db, page_size=1)["total_pages"] == 6

    def test_condition_25_out_of_range_page_returns_empty_items(self, in_memory_db):
        """Scenario 25: Requesting page beyond total_pages returns items=[] with correct total and total_pages."""
        _seed_sample_records(in_memory_db)
        result = get_feedback_records(in_memory_db, page=99, page_size=10)
        assert result["items"] == []
        assert result["total"] == 6
        assert result["page"] == 99
        assert result["page_size"] == 10
        assert result["total_pages"] == 1


class TestFeedbackRecordsAPIEndpoint:
    """Validates HTTP contract, status codes, query parameters, and error handling."""

    def test_condition_22_api_response_schema_and_headers(self, client, in_memory_db):
        """Scenario 22: GET /api/v1/feedback/records returns HTTP 200 with complete validated schema."""
        _seed_sample_records(in_memory_db)
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback/records?page=1&page_size=10")
            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "total_pages" in data

            assert data["total"] == 6
            assert data["page"] == 1
            assert data["page_size"] == 10
            assert data["total_pages"] == 1
            assert len(data["items"]) == 6

            # Verify individual item schema fields
            item = data["items"][0]
            expected_fields = {
                "id", "department", "semester", "feedback_text", "clean_text",
                "sentiment_label", "sentiment_name", "sentiment_confidence",
                "category_name", "category_confidence",
                "priority_score", "priority_level", "priority_reason", "created_at"
            }
            assert set(item.keys()) == expected_fields
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_query_filtering(self, client, in_memory_db):
        """Validates query parameters via HTTP GET."""
        _seed_sample_records(in_memory_db)
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # Search
            res = client.get("/api/v1/feedback/records?search=calculus")
            assert res.status_code == 200
            assert res.json()["total"] == 1

            # Sentiment (case-insensitive)
            res = client.get("/api/v1/feedback/records?sentiment=Negative")
            assert res.status_code == 200
            assert res.json()["total"] == 2

            # Priority (case-insensitive)
            res = client.get("/api/v1/feedback/records?priority=HIGH")
            assert res.status_code == 200
            assert res.json()["total"] == 2

            # Category
            res = client.get("/api/v1/feedback/records?category=Teaching")
            assert res.status_code == 200
            assert res.json()["total"] == 2

            # Combined
            res = client.get(
                "/api/v1/feedback/records?category=Teaching&sentiment=negative&priority=high"
            )
            assert res.status_code == 200
            assert res.json()["total"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_invalid_sentiment_returns_422(self, client, in_memory_db):
        """Scenario 14 (HTTP): Invalid sentiment query param returns HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback/records?sentiment=unknown")
            assert response.status_code == 422
            assert "Invalid sentiment filter" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_invalid_priority_returns_422(self, client, in_memory_db):
        """Scenario 15 (HTTP): Invalid priority query param returns HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback/records?priority=urgent")
            assert response.status_code == 422
            assert "Invalid priority filter" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_26_invalid_pagination_bounds_return_422(self, client, in_memory_db):
        """Scenario 26: page < 1, page_size < 1, or page_size > 100 returns HTTP 422 via FastAPI validation."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res_page = client.get("/api/v1/feedback/records?page=0")
            assert res_page.status_code == 422

            res_size_low = client.get("/api/v1/feedback/records?page_size=0")
            assert res_size_low.status_code == 422

            res_size_high = client.get("/api/v1/feedback/records?page_size=101")
            assert res_size_high.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_condition_24_database_failure_returns_safe_500(self, client, in_memory_db):
        """Scenario 24: SQLAlchemyError triggers HTTP 500 without leaking stack traces."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            with patch(
                "app.api.v1.endpoints.feedback.get_feedback_records",
                side_effect=SQLAlchemyError("Simulated DB connection failure"),
            ):
                response = client.get("/api/v1/feedback/records")
                assert response.status_code == 500
                assert response.json()["detail"] == (
                    "Failed to retrieve feedback records due to an internal database error."
                )
        finally:
            app.dependency_overrides.clear()


class TestExistingEndpointsRegression:
    """Scenario 23: Confirms all existing feedback and analysis endpoints continue functioning identically."""

    def test_existing_list_feedback_functional(self, client, in_memory_db):
        """GET /api/v1/feedback remains functional."""
        _seed_sample_records(in_memory_db)
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback")
            assert response.status_code == 200
            assert len(response.json()) == 6
        finally:
            app.dependency_overrides.clear()

    def test_existing_feedback_stats_functional(self, client, in_memory_db):
        """GET /api/v1/feedback/stats remains functional alongside GET /records."""
        _seed_sample_records(in_memory_db)
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_feedback"] == 6
            assert data["analyzed_feedback"] == 5
            assert data["unclassified_feedback"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_existing_feedback_submission_functional(self, client, in_memory_db):
        """POST /api/v1/feedback remains functional."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {
                "department": "Mechanical Engineering",
                "semester": "Semester 5",
                "feedback_text": "Need more modern equipment in thermodynamics lab.",
            }
            response = client.post("/api/v1/feedback", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["id"] > 0
            assert data["feedback_text"] == payload["feedback_text"]
        finally:
            app.dependency_overrides.clear()

    def test_existing_analyze_and_save_functional(self, client, in_memory_db):
        """POST /api/v1/feedback/analyze-and-save remains functional."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {
                "feedback": "The professor is very helpful and explains concepts clearly.",
                "department": "Computer Science",
                "semester": "Semester 4",
            }
            response = client.post("/api/v1/feedback/analyze-and-save", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["id"] > 0
            assert data["sentiment_name"] in {"positive", "neutral", "negative"}
        finally:
            app.dependency_overrides.clear()
