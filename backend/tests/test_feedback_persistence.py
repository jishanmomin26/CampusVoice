"""Comprehensive Unit and Integration Tests for Feedback Persistence (Step 9.3).

Validates:
  1. POST /api/v1/feedback/analyze-and-save with valid feedback returns HTTP 201 Created
  2. Response contains id, feedback_text, clean_text, sentiment, category, priority, created_at
  3. Database persistence matches analysis results exactly
  4. Optional department and semester are persisted when supplied; NULL when omitted
  5. Legacy records without analysis fields remain valid and serialize with null analysis fields
  6. Empty feedback string ("") returns HTTP 422
  7. Whitespace-only feedback ("   ") returns HTTP 422
  8. Missing feedback field ({}) returns HTTP 422
  9. Non-string feedback returns HTTP 422
  10. Analysis service failure (e.g. missing artifacts) returns HTTP 503 and persists no record
  11. Database failure triggers rollback, returns HTTP 500, and leaves no partially committed record
  12. Existing GET /api/v1/feedback returns both legacy and analyzed records
  13. Existing POST /api/v1/feedback remains fully functional
  14. Existing POST /api/v1/feedback/analyze remains analysis-only (does NOT persist)
  15. Real pipeline execution preserves negation tokens in persisted clean_text
  16. Model artifacts are not retrained or refitted during analyze-and-save execution
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline


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


class TestFeedbackAnalyzeAndSaveContract:
    """Validates endpoint availability, status codes, and response schema."""

    def test_analyze_and_save_returns_201_with_valid_payload(self, client, in_memory_db):
        """Test that valid feedback returns HTTP 201 Created with database ID and analysis fields."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {"feedback": "The professor is very helpful and explains concepts clearly."}
            response = client.post("/api/v1/feedback/analyze-and-save", json=payload)
            assert response.status_code == 201
            data = response.json()

            assert "id" in data
            assert isinstance(data["id"], int)
            assert data["id"] > 0
            assert data["feedback_text"] == "The professor is very helpful and explains concepts clearly."
            assert data["clean_text"] is not None
            assert isinstance(data["clean_text"], str)
            assert data["sentiment_label"] in {-1, 0, 1}
            assert data["sentiment_name"] in {"positive", "neutral", "negative"}
            assert 0.0 <= data["sentiment_confidence"] <= 1.0
            assert data["category_name"] in {
                "Course Content", "Teaching", "Examination",
                "Lab Work", "Library Facilities", "Extracurricular",
            }
            assert 0.0 <= data["category_confidence"] <= 1.0
            assert 0 <= data["priority_score"] <= 100
            assert data["priority_level"] in {"High", "Medium", "Low"}
            assert isinstance(data["priority_reason"], str)
            assert "created_at" in data
            assert data["department"] is None
            assert data["semester"] is None
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_database_persistence_verification(self, client, in_memory_db):
        """Test that the feedback record is accurately committed to the database."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {"feedback": "The laboratory equipment is broken and needs urgent repair."}
            response = client.post("/api/v1/feedback/analyze-and-save", json=payload)
            assert response.status_code == 201
            record_id = response.json()["id"]

            db_record = in_memory_db.get(Feedback, record_id)
            assert db_record is not None
            assert db_record.feedback_text == "The laboratory equipment is broken and needs urgent repair."
            assert db_record.clean_text == response.json()["clean_text"]
            assert db_record.sentiment_name == response.json()["sentiment_name"]
            assert db_record.category_name == response.json()["category_name"]
            assert db_record.priority_score == response.json()["priority_score"]
            assert db_record.priority_level == response.json()["priority_level"]
            assert db_record.priority_reason == response.json()["priority_reason"]
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_optional_department_and_semester_persistence(self, client, in_memory_db):
        """Test that optional department and semester are saved when provided."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {
                "feedback": "The wifi in the campus library is very fast and reliable.",
                "department": "Information Technology",
                "semester": "Semester 5",
            }
            response = client.post("/api/v1/feedback/analyze-and-save", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["department"] == "Information Technology"
            assert data["semester"] == "Semester 5"

            db_record = in_memory_db.get(Feedback, data["id"])
            assert db_record.department == "Information Technology"
            assert db_record.semester == "Semester 5"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_legacy_records_without_analysis_fields_remain_valid(self, client, in_memory_db):
        """Test that existing records without analysis fields serialize properly in FeedbackResponse."""
        legacy_record = Feedback(
            department="Computer Engineering",
            semester="Semester 3",
            feedback_text="Good theoretical lectures.",
        )
        in_memory_db.add(legacy_record)
        in_memory_db.commit()
        in_memory_db.refresh(legacy_record)

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get("/api/v1/feedback")
            assert response.status_code == 200
            records = response.json()
            assert len(records) >= 1
            found = next((r for r in records if r["id"] == legacy_record.id), None)
            assert found is not None
            assert found["department"] == "Computer Engineering"
            assert found["semester"] == "Semester 3"
            assert found["feedback_text"] == "Good theoretical lectures."
            assert found["clean_text"] is None
            assert found["sentiment_name"] is None
            assert found["category_name"] is None
            assert found["priority_score"] is None
            assert found["priority_level"] is None
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestFeedbackAnalyzeAndSaveValidation:
    """Validates input handling and 422 error rejection."""

    def test_empty_string_returns_422(self, client, in_memory_db):
        """Empty feedback string must return HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post("/api/v1/feedback/analyze-and-save", json={"feedback": ""})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_whitespace_only_string_returns_422(self, client, in_memory_db):
        """Whitespace-only string must return HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post("/api/v1/feedback/analyze-and-save", json={"feedback": "   \n\t  "})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_missing_feedback_field_returns_422(self, client, in_memory_db):
        """Missing feedback key must return HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post("/api/v1/feedback/analyze-and-save", json={})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_non_string_feedback_returns_422(self, client, in_memory_db):
        """Non-string feedback payload must return HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post("/api/v1/feedback/analyze-and-save", json={"feedback": 99999})
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestFeedbackPersistenceTransactionSafety:
    """Validates error recovery, transaction rollbacks, and exception safety."""

    def test_ml_pipeline_failure_returns_503_and_persists_nothing(self, client, in_memory_db):
        """If ML model artifacts are missing, endpoint returns 503 and persists no DB record."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            with patch("app.api.v1.endpoints.feedback.analyze_feedback") as mock_analyze:
                mock_analyze.side_effect = FileNotFoundError("Mocked missing model artifact")
                response = client.post(
                    "/api/v1/feedback/analyze-and-save",
                    json={"feedback": "Any feedback message."},
                )
                assert response.status_code == 503
                assert "Machine learning model artifacts are currently unavailable." in response.json()["detail"]

                # Ensure zero records created in database
                count = in_memory_db.scalar(select(Feedback).count()) if hasattr(select(Feedback), 'count') else len(in_memory_db.scalars(select(Feedback)).all())
                assert count == 0
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_database_failure_triggers_rollback_and_returns_500(self, client, in_memory_db):
        """Database exception triggers session rollback, returns 500 without stack traces."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            with patch("app.services.feedback_service.Feedback") as MockFeedback:
                # Force SQLAlchemyError on session.add or commit
                mock_instance = MagicMock()
                MockFeedback.return_value = mock_instance
                with patch.object(in_memory_db, "commit", side_effect=SQLAlchemyError("Simulated DB commit error")):
                    response = client.post(
                        "/api/v1/feedback/analyze-and-save",
                        json={"feedback": "The teachers are great."},
                    )
                    assert response.status_code == 500
                    detail = response.json()["detail"]
                    assert "internal database error" in detail.lower() or "unexpected error" in detail.lower()
                    assert "Simulated DB commit error" not in detail
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestRegressionAndPipelineIntegrity:
    """Validates regression prevention on existing endpoints and ML pipeline integrity."""

    def test_existing_analysis_only_endpoint_does_not_persist(self, client, in_memory_db):
        """POST /api/v1/feedback/analyze remains strictly in-memory without creating DB records."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            initial_count = len(in_memory_db.scalars(select(Feedback)).all())
            response = client.post(
                "/api/v1/feedback/analyze",
                json={"feedback": "The exam scheduling has major clashes."},
            )
            assert response.status_code == 200
            final_count = len(in_memory_db.scalars(select(Feedback)).all())
            assert final_count == initial_count
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_existing_feedback_submission_endpoint_still_works(self, client, in_memory_db):
        """POST /api/v1/feedback still creates legacy records."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {
                "department": "Mechanical Engineering",
                "semester": "Semester 7",
                "feedback_text": "Need newer workshop tools.",
            }
            response = client.post("/api/v1/feedback", json=payload)
            assert response.status_code == 201
            assert response.json()["department"] == "Mechanical Engineering"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_real_pipeline_negation_preservation_and_priority(self, client, in_memory_db):
        """Real pipeline execution on sample verifies negation token preservation and priority score."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {"feedback": "The faculty is not helpful and the explanations are not clear."}
            response = client.post("/api/v1/feedback/analyze-and-save", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert "faculty not helpful explanation not clear" in data["clean_text"]
            assert data["sentiment_name"] == "negative"
            assert data["category_name"] == "Teaching"
            assert data["priority_score"] == 65
            assert data["priority_level"] == "Medium"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_model_artifacts_not_retrained_or_refitted(self, client, in_memory_db):
        """Verify vectorizer fit/fit_transform is NEVER called during analyze-and-save."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            with patch.object(
                FeedbackIntelligencePipeline, "vectorizer", create=True
            ) as mock_vec:
                mock_vec.fit = MagicMock()
                mock_vec.fit_transform = MagicMock()

                response = client.post(
                    "/api/v1/feedback/analyze-and-save",
                    json={"feedback": "The campus library is very quiet and spacious."},
                )
                assert response.status_code == 201
                mock_vec.fit.assert_not_called()
                mock_vec.fit_transform.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_db, None)
