"""Comprehensive Unit Tests for NLP Preprocessing Pipeline."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nlp.preprocessing import (
    normalize_text,
    preprocess_text,
    tokenize_text,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as c:
        yield c


class TestTextNormalization:
    """Tests for basic text normalization functions."""

    def test_basic_normalization(self):
        raw = "  Hello CampusVoice!  "
        normalized = normalize_text(raw)
        assert normalized == "hello campusvoice!"

    def test_lowercasing(self):
        raw = "STUDENT Feedback INTELLIGENCE"
        normalized = normalize_text(raw)
        assert normalized == "student feedback intelligence"

    def test_whitespace_normalization(self):
        raw = "Line 1\n\nLine 2\t\twith   multiple     spaces.  "
        normalized = normalize_text(raw)
        assert normalized == "line 1 line 2 with multiple spaces."

    def test_empty_input(self):
        assert normalize_text("") == ""
        assert normalize_text(None) == ""

    def test_whitespace_only_input(self):
        assert normalize_text("   \t  \n  ") == ""


class TestTokenizationAndLemmatization:
    """Tests for tokenization, stopword removal, and lemmatization."""

    def test_tokenization(self):
        text = "The practical sessions are informative."
        tokens = tokenize_text(text)
        assert "practical" in tokens
        assert "sessions" in tokens
        assert "informative" in tokens

    def test_stopword_removal_with_negation_preservation(self):
        """Verify standard stopwords are removed but sentiment negations ('not', 'no', 'never') are retained."""
        text = "The faculty is not helpful at all."
        result = preprocess_text(text)

        # 'the', 'is', 'at', 'all' are stopwords and should be removed
        assert "is" not in result.filtered_tokens
        assert "at" not in result.filtered_tokens

        # Core words must be present
        assert "faculty" in result.filtered_tokens
        assert "helpful" in result.filtered_tokens

        # CRITICAL: Negation 'not' must be strictly preserved!
        assert "not" in result.filtered_tokens
        assert "not" in result.lemmatized_tokens
        assert "not" in result.clean_text

        # Must NOT be reduced to positive sentiment "faculty helpful"
        assert result.clean_text != "faculty helpful"
        assert "not" in result.clean_text.split()

    def test_additional_negations_preserved(self):
        """Verify 'no' and 'never' are also preserved."""
        res_no = preprocess_text("We have no access to the lab equipment.")
        assert "no" in res_no.filtered_tokens
        assert "no" in res_no.clean_text.split()

        res_never = preprocess_text("The lab assistant was never present.")
        assert "never" in res_never.filtered_tokens
        assert "never" in res_never.clean_text.split()

    def test_contraction_negation_preserved(self):
        """Contractions like isn't, aren't should preserve negation 'not'."""
        res = preprocess_text("The internet isn't working.")
        assert "not" in res.filtered_tokens
        assert "not" in res.clean_text.split()

    def test_lemmatization(self):
        """Verify morphological root reduction without brittle exact version coupling."""
        text = "students were learning better concepts"
        result = preprocess_text(text)

        lemmas = result.lemmatized_tokens
        # Check that plurals are reduced to singular root
        assert "student" in lemmas or "students" in result.tokens
        assert "student" in lemmas
        # Check that inflected verbs are reduced to base form
        assert "learn" in lemmas
        # Check that concepts is reduced to concept
        assert "concept" in lemmas

    def test_empty_and_whitespace_edge_cases(self):
        """Verify empty and blank strings produce clean, safe empty results without errors."""
        res_empty = preprocess_text("")
        assert res_empty.tokens == []
        assert res_empty.filtered_tokens == []
        assert res_empty.lemmatized_tokens == []
        assert res_empty.clean_text == ""

        res_spaces = preprocess_text("    \n\t   ")
        assert res_spaces.tokens == []
        assert res_spaces.clean_text == ""

    def test_punctuation_heavy_input(self):
        """Verify punctuation-heavy text retains word content while discarding standalone symbols."""
        text = "Excellent lab!!! Really, really awesome... 100% recommended :)"
        result = preprocess_text(text)

        assert "!" not in result.tokens
        assert "..." not in result.tokens
        assert "excellent" in result.tokens
        assert "lab" in result.tokens

    def test_realistic_student_feedback(self):
        """Verify realistic feedback from Step 3 specification."""
        text = (
            "The practical sessions are very useful! The faculty explains "
            "concepts clearly, but the lab computers are sometimes slow."
        )
        result = preprocess_text(text)

        assert result.original_text == text
        assert "practical sessions" in result.normalized_text
        assert len(result.tokens) > 0
        assert len(result.filtered_tokens) > 0
        assert len(result.lemmatized_tokens) > 0

        # Core semantic tokens must be captured
        clean = result.clean_text
        assert "practical" in clean
        assert "session" in clean or "practical" in clean
        assert "faculty" in clean
        assert "computer" in clean or "slow" in clean


class TestNLPAPIEndpoint:
    """Tests for the POST /api/v1/nlp/preprocess API endpoint."""

    def test_api_preprocess_endpoint(self, client):
        payload = {
            "text": "The practical sessions are very useful and the faculty explains concepts clearly."
        }
        response = client.post("/api/v1/nlp/preprocess", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "original_text" in data
        assert "normalized_text" in data
        assert "tokens" in data
        assert "filtered_tokens" in data
        assert "lemmatized_tokens" in data
        assert "clean_text" in data

        assert data["original_text"] == payload["text"]
        assert "faculty" in data["clean_text"]
        assert len(data["tokens"]) > 0

    def test_api_preprocess_negation_preservation(self, client):
        payload = {"text": "The faculty is not helpful."}
        response = client.post("/api/v1/nlp/preprocess", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "not" in data["clean_text"].split()
        assert data["clean_text"] != "faculty helpful"
