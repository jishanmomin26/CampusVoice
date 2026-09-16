"""Tests for spaCy Model Installation & Verification (Step 9.18.3).

Validates:
1. Build-time spaCy model installer executes and verifies successfully.
2. get_spacy_model() returns a valid, functional spacy.Language pipeline.
3. spaCy model caching functions as a singleton across multiple invocations.
4. Core NLP capabilities required by the application (tokenization, lemmatization) work accurately.
5. High-speed configuration (NER disabled) is preserved.
6. Missing/unknown model requests raise MissingNLPResourceError without runtime downloads.
"""

import pytest
import spacy

from app.nlp.resources import (
    MissingNLPResourceError,
    get_spacy_model,
)
from scripts.install_spacy_model import install_and_verify_model


class TestSpaCyModelConfiguration:
    """Validates build-time model installation, lazy loading, and NLP capabilities."""

    def test_install_and_verify_model_succeeds(self):
        """Build-time installer verifies en_core_web_sm successfully."""
        result = install_and_verify_model("en_core_web_sm")
        assert result is True

    def test_get_spacy_model_returns_language_instance(self):
        """get_spacy_model() returns a valid spacy.Language pipeline."""
        nlp = get_spacy_model()
        assert nlp is not None
        assert isinstance(nlp, spacy.Language)

    def test_get_spacy_model_caches_instance(self):
        """get_spacy_model() caches the loaded instance to prevent redundant loading."""
        nlp1 = get_spacy_model()
        nlp2 = get_spacy_model()
        assert nlp1 is nlp2

    def test_spacy_model_tokenization_and_lemmatization(self):
        """Model produces expected tokens, lemmas, and linguistic flags."""
        nlp = get_spacy_model()
        doc = nlp("The practical sessions are very informative.")

        tokens = [token.text for token in doc]
        assert "practical" in tokens
        assert "sessions" in tokens
        assert "informative" in tokens

        # Validate lemmatization capability
        token_map = {token.text: token for token in doc}
        assert token_map["sessions"].lemma_ == "session"
        assert token_map["are"].lemma_ == "be"

        # Validate token classification flags
        assert not token_map["practical"].is_punct
        assert not token_map["practical"].is_space

    def test_spacy_model_disables_ner_for_speed(self):
        """Named Entity Recognition (NER) is disabled for high-speed preprocessing."""
        nlp = get_spacy_model()
        assert "ner" not in nlp.pipe_names

    def test_missing_model_raises_missing_resource_error(self):
        """Attempting to load a nonexistent model raises MissingNLPResourceError."""
        with pytest.raises(MissingNLPResourceError) as exc_info:
            get_spacy_model("nonexistent_model_package_xyz")
        assert "is not installed" in str(exc_info.value)
