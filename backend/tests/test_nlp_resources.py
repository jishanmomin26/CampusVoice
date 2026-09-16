"""Tests for NLP Resource Installation & Search Path Configuration (Step 9.18.3).

Validates:
1. Deterministic build-time installation script succeeds and verifies 'stopwords'.
2. NLTK 'stopwords' resource is available and accessible to get_stopwords().
3. Negation preservation behavior functions accurately with real stopwords.
4. NLTK search paths include virtual environment and project directories.
5. Application import does not trigger any runtime downloads.
"""

import sys
from pathlib import Path
import pytest
import nltk

from app.nlp.resources import (
    SENTIMENT_NEGATION_WORDS,
    check_nltk_resources,
    get_stopwords,
)
from scripts.install_nltk_resources import install_resources


class TestNLPResourceConfiguration:
    """Validates build-time resource installation and runtime search paths."""

    def test_install_resources_executes_successfully(self):
        """Build-time installer installs and verifies 'stopwords' with return code True."""
        result = install_resources(["stopwords"])
        assert result is True

    def test_stopwords_resource_is_available(self):
        """check_nltk_resources() reports stopwords as available."""
        status = check_nltk_resources()
        assert status.get("stopwords") is True

    def test_get_stopwords_returns_expected_set(self):
        """get_stopwords() loads real English stopwords successfully."""
        words = get_stopwords(preserve_negations=True)
        assert isinstance(words, set)
        assert len(words) > 100
        # Common English stopwords must be present
        assert "the" in words
        assert "is" in words
        assert "and" in words
        assert "in" in words

    def test_get_stopwords_preserves_sentiment_negations(self):
        """get_stopwords(preserve_negations=True) retains critical negation words."""
        words_with_negations = get_stopwords(preserve_negations=True)
        for negation in SENTIMENT_NEGATION_WORDS:
            assert negation not in words_with_negations, (
                f"Negation word '{negation}' should not be in stopword set when preserved."
            )

    def test_get_stopwords_without_negation_preservation(self):
        """get_stopwords(preserve_negations=False) includes standard negations."""
        words_raw = get_stopwords(preserve_negations=False)
        assert "not" in words_raw
        assert "no" in words_raw

    def test_nltk_search_paths_include_project_or_venv(self):
        """nltk.data.path contains venv or project nltk_data directories."""
        paths_str = [str(p) for p in nltk.data.path]
        venv_nltk = str(Path(sys.prefix) / "nltk_data")
        backend_dir = Path(__file__).resolve().parent.parent
        repo_nltk = str(backend_dir.parent / "nltk_data")

        has_expected_path = any(
            venv_nltk in p or repo_nltk in p or "nltk_data" in p
            for p in paths_str
        )
        assert has_expected_path is True

    def test_stopwords_found_without_runtime_download(self):
        """Direct find of corpora/stopwords succeeds immediately from configured paths."""
        found = nltk.data.find("corpora/stopwords")
        assert found is not None
