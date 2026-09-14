"""Comprehensive Unit and Integration Tests for Feedback Analysis API Endpoint (Step 9.1).

Validates 18 distinct conditions:
  1. Endpoint exists at POST /api/v1/feedback/analyze
  2. Valid feedback returns HTTP 200 OK
  3. Response contains feedback, clean_text, sentiment, category, models, priority
  4. Sentiment response contains label, name, confidence, probabilities
  5. Category response contains name, confidence, probabilities
  6. Priority response contains score, level, reason
  7. Priority score is an integer bounded in [0, 100]
  8. Priority level belongs strictly to {'High', 'Medium', 'Low'}
  9. Empty feedback string ("") returns HTTP 422
  10. Whitespace-only feedback ("   ") returns HTTP 422
  11. Missing feedback field ({}) returns HTTP 422
  12. Non-string feedback ({"feedback": 12345}) returns HTTP 422
  13. Existing feedback creation endpoint (POST /api/v1/feedback) remains functional
  14. Existing NLP preprocessing endpoint (POST /api/v1/nlp/preprocess) remains functional
  15. Existing health endpoints (GET /health, GET /api/v1/health) remain functional
  16. Real pipeline integration preserves negation in clean_text
  17. Endpoint delegates to ML layer without duplicating priority scoring logic
  18. Model artifacts are not retrained or refitted during API inference
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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


class TestFeedbackAnalysisEndpointContract:
    """Validates endpoint availability, routing, and schema structure (Conditions 1-8)."""

    def test_condition_1_endpoint_exists(self, client):
        """Condition 1: POST /api/v1/feedback/analyze is reachable (not 404)."""
        response = client.post("/api/v1/feedback/analyze", json={"feedback": "Good teaching."})
        assert response.status_code != 404

    def test_condition_2_valid_feedback_returns_200(self, client):
        """Condition 2: Valid feedback payload returns HTTP 200 OK."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "The professor is very helpful and explains concepts clearly."},
        )
        assert response.status_code == 200

    def test_condition_3_response_contains_all_top_level_fields(self, client):
        """Condition 3: Response contains feedback, clean_text, sentiment, category, models, priority."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "The campus library has a quiet study room."},
        )
        assert response.status_code == 200
        data = response.json()
        required_keys = {"feedback", "clean_text", "sentiment", "category", "models", "priority"}
        assert required_keys.issubset(data.keys())
        assert data["feedback"] == "The campus library has a quiet study room."
        assert isinstance(data["clean_text"], str)

    def test_condition_4_sentiment_contains_required_fields(self, client):
        """Condition 4: Sentiment contains label, name, confidence, probabilities."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "Great curriculum and modern topics."},
        )
        assert response.status_code == 200
        sentiment = response.json()["sentiment"]
        assert "label" in sentiment
        assert "name" in sentiment
        assert "confidence" in sentiment
        assert "probabilities" in sentiment
        assert sentiment["label"] in {-1, 0, 1}
        assert 0.0 <= sentiment["confidence"] <= 1.0
        assert isinstance(sentiment["probabilities"], dict)

    def test_condition_5_category_contains_required_fields(self, client):
        """Condition 5: Category contains name, confidence, probabilities."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "The laboratory computers are not functioning properly."},
        )
        assert response.status_code == 200
        category = response.json()["category"]
        assert "name" in category
        assert "confidence" in category
        assert "probabilities" in category
        assert 0.0 <= category["confidence"] <= 1.0
        assert len(category["probabilities"]) == 6

    def test_condition_6_priority_contains_required_fields(self, client):
        """Condition 6: Priority contains score, level, reason."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "Examination schedules clashed and timetable was published late."},
        )
        assert response.status_code == 200
        priority = response.json()["priority"]
        assert "score" in priority
        assert "level" in priority
        assert "reason" in priority

    def test_condition_7_priority_score_bounded(self, client):
        """Condition 7: Priority score is an integer between 0 and 100."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "Extracurricular hackathons are well organized."},
        )
        assert response.status_code == 200
        score = response.json()["priority"]["score"]
        assert isinstance(score, int)
        assert not isinstance(score, bool)
        assert 0 <= score <= 100

    def test_condition_8_priority_level_valid_tier(self, client):
        """Condition 8: Priority level is one of High, Medium, Low."""
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": "The cafeteria facilities need cleanliness improvements."},
        )
        assert response.status_code == 200
        level = response.json()["priority"]["level"]
        assert level in {"High", "Medium", "Low"}


class TestFeedbackAnalysisInputValidation:
    """Validates request rejection and error handling (Conditions 9-12)."""

    def test_condition_9_empty_feedback_rejected(self, client):
        """Condition 9: Empty feedback string returns HTTP 422."""
        response = client.post("/api/v1/feedback/analyze", json={"feedback": ""})
        assert response.status_code == 422

    def test_condition_10_whitespace_feedback_rejected(self, client):
        """Condition 10: Whitespace-only feedback returns HTTP 422."""
        response = client.post("/api/v1/feedback/analyze", json={"feedback": "   \n\t  "})
        assert response.status_code == 422

    def test_condition_11_missing_feedback_field_rejected(self, client):
        """Condition 11: Missing feedback field returns HTTP 422."""
        response = client.post("/api/v1/feedback/analyze", json={})
        assert response.status_code == 422

    def test_condition_12_non_string_feedback_rejected(self, client):
        """Condition 12: Non-string feedback returns HTTP 422."""
        response = client.post("/api/v1/feedback/analyze", json={"feedback": 12345})
        assert response.status_code == 422

        response_list = client.post(
            "/api/v1/feedback/analyze", json={"feedback": ["Great course"]}
        )
        assert response_list.status_code == 422


class TestExistingEndpointsRegression:
    """Validates that existing endpoints continue functioning without regression (Conditions 13-15)."""

    def test_condition_13_existing_feedback_creation_functional(self, client, in_memory_db):
        """Condition 13: Existing POST /api/v1/feedback remains functional."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            payload = {
                "department": "Computer Science",
                "semester": "Semester 4",
                "feedback_text": "Good laboratory practical environment.",
            }
            response = client.post("/api/v1/feedback", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["department"] == "Computer Science"
            assert data["semester"] == "Semester 4"
            assert data["feedback_text"] == "Good laboratory practical environment."
            assert "id" in data
            assert "created_at" in data
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_condition_14_existing_nlp_preprocess_functional(self, client):
        """Condition 14: Existing POST /api/v1/nlp/preprocess remains functional."""
        response = client.post(
            "/api/v1/nlp/preprocess",
            json={"text": "The faculty is not helpful at all."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "clean_text" in data
        assert "tokens" in data
        assert "not" in data["clean_text"].lower().split()

    def test_condition_15_existing_health_endpoints_functional(self, client):
        """Condition 15: GET /health and GET /api/v1/health return HTTP 200."""
        root_health = client.get("/health")
        assert root_health.status_code == 200
        assert root_health.json()["status"] == "healthy"

        v1_health = client.get("/api/v1/health")
        assert v1_health.status_code == 200
        assert v1_health.json()["status"] == "healthy"


class TestMLPipelineIntegrationBehavior:
    """Validates real ML integration, negation preservation, and immutability (Conditions 16-18)."""

    def test_condition_16_real_pipeline_preserves_negation(self, client):
        """Condition 16: Real pipeline invocation preserves negation in clean_text."""
        raw_text = "The faculty is not helpful and the explanations are not clear at all."
        response = client.post(
            "/api/v1/feedback/analyze",
            json={"feedback": raw_text},
        )
        assert response.status_code == 200
        data = response.json()

        # Negations preserved
        clean_tokens = data["clean_text"].lower().split()
        assert "not" in clean_tokens

        # Sentiment detected as negative
        assert data["sentiment"]["name"] == "negative"
        assert data["sentiment"]["label"] == -1

        # Priority appropriately computed
        assert data["priority"]["level"] in {"High", "Medium"}
        assert data["priority"]["score"] >= 50

    def test_condition_17_endpoint_delegates_to_ml_layer(self, client):
        """Condition 17: Endpoint delegates directly to analyze_feedback without duplicating scoring logic."""
        with patch(
            "app.api.v1.endpoints.analysis.analyze_feedback"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "feedback": "Custom mock text.",
                "clean_text": "custom mock text",
                "sentiment": {
                    "label": 1,
                    "name": "positive",
                    "confidence": 0.95,
                    "probabilities": {"positive": 0.95, "neutral": 0.03, "negative": 0.02},
                },
                "category": {
                    "name": "Teaching",
                    "confidence": 0.88,
                    "probabilities": {
                        "Teaching": 0.88,
                        "Course Content": 0.04,
                        "Examination": 0.02,
                        "Lab Work": 0.02,
                        "Library Facilities": 0.02,
                        "Extracurricular": 0.02,
                    },
                },
                "models": {
                    "sentiment": "logistic_regression",
                    "category": "logistic_regression",
                },
                "priority": {
                    "score": 20,
                    "level": "Low",
                    "reason": "Positive feedback indicates low immediate action priority.",
                },
            }

            response = client.post(
                "/api/v1/feedback/analyze",
                json={"feedback": "Custom mock text."},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["priority"]["score"] == 20
            assert data["priority"]["level"] == "Low"
            assert mock_analyze.called

    def test_condition_18_no_model_refitting_during_api_call(self, client):
        """Condition 18: TF-IDF vectorizer is never refitted during API inference."""
        from ml.pipeline.feedback_intelligence import _cached_pipeline

        # Ensure pipeline is initialized
        client.post("/api/v1/feedback/analyze", json={"feedback": "Testing vectorizer stability."})

        from ml.pipeline import feedback_intelligence
        pipeline = feedback_intelligence._cached_pipeline
        assert pipeline is not None

        vectorizer = pipeline._vectorizer
        vectorizer.fit = MagicMock(side_effect=RuntimeError("fit() must not be called in API"))
        vectorizer.fit_transform = MagicMock(
            side_effect=RuntimeError("fit_transform() must not be called in API")
        )

        try:
            response = client.post(
                "/api/v1/feedback/analyze",
                json={"feedback": "New term verification."},
            )
            assert response.status_code == 200
            assert vectorizer.fit.call_count == 0
            assert vectorizer.fit_transform.call_count == 0
        finally:
            del vectorizer.fit
            del vectorizer.fit_transform
