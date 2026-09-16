"""NLP Resource Management for NLTK and spaCy."""

import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Set
import nltk

logger = logging.getLogger(__name__)

# Register project-level and environment nltk_data search paths if present
_CURRENT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CURRENT_DIR.parent.parent
_REPO_ROOT = _BACKEND_DIR.parent

for _search_path in (_REPO_ROOT / "nltk_data", _BACKEND_DIR / "nltk_data", Path(sys.prefix) / "nltk_data"):
    _str_path = str(_search_path)
    if _search_path.is_dir() and _str_path not in nltk.data.path:
        nltk.data.path.insert(0, _str_path)

# Required NLTK corpora and tokenizers
REQUIRED_NLTK_RESOURCES = {
    "tokenizers/punkt": "punkt",
    "tokenizers/punkt_tab": "punkt_tab",
    "corpora/stopwords": "stopwords",
    "corpora/wordnet": "wordnet",
    "corpora/omw-1.4": "omw-1.4",
}

# Words critical for sentiment analysis context that must NOT be stripped as stopwords
SENTIMENT_NEGATION_WORDS: Set[str] = {
    "not",
    "no",
    "never",
    "n't",
    "neither",
    "nor",
    "none",
    "cannot",
    "without",
    "hardly",
    "barely",
    "scarcely",
}

# Cached instances
_spacy_model = None
_cached_spacy_models: Dict[str, Any] = {}
_cached_stopwords: Optional[Set[str]] = None


class MissingNLPResourceError(Exception):
    """Raised when a required NLTK resource or spaCy model is missing."""

    pass


def check_nltk_resources() -> Dict[str, bool]:
    """Check availability of required NLTK resources without downloading.

    Returns:
        Dict[str, bool]: Mapping of resource name to availability boolean.
    """
    status: Dict[str, bool] = {}
    for resource_path, download_name in REQUIRED_NLTK_RESOURCES.items():
        try:
            nltk.data.find(resource_path)
            status[download_name] = True
        except (LookupError, OSError):
            status[download_name] = False
    return status


def download_nltk_resources(quiet: bool = False) -> None:
    """Download required NLTK resources explicitly when requested.

    Args:
        quiet (bool): Suppress download output if True.
    """
    for resource_path, download_name in REQUIRED_NLTK_RESOURCES.items():
        try:
            nltk.data.find(resource_path)
            if not quiet:
                logger.info("NLTK resource '%s' already exists.", download_name)
        except (LookupError, OSError):
            if not quiet:
                logger.info("Downloading missing NLTK resource: %s...", download_name)
            nltk.download(download_name, quiet=quiet)


def get_stopwords(
    preserve_negations: bool = True,
    custom_stopwords: Optional[Set[str]] = None,
) -> Set[str]:
    """Retrieve English stopwords from NLTK with negation preservation.

    Args:
        preserve_negations (bool): If True, retains words like 'not', 'no', 'never'.
        custom_stopwords (Optional[Set[str]]): Additional words to exclude.

    Returns:
        Set[str]: Set of stopwords.

    Raises:
        MissingNLPResourceError: If NLTK 'stopwords' corpus is not installed.
    """
    global _cached_stopwords
    try:
        nltk.data.find("corpora/stopwords")
    except (LookupError, OSError):
        raise MissingNLPResourceError(
            "NLTK 'stopwords' resource is missing. "
            "Please run: python -m app.nlp.resources --download"
        )

    if _cached_stopwords is None:
        from nltk.corpus import stopwords

        base_stopwords = set(stopwords.words("english"))
        _cached_stopwords = base_stopwords

    words = set(_cached_stopwords)
    if preserve_negations:
        words -= SENTIMENT_NEGATION_WORDS

    if custom_stopwords:
        words |= custom_stopwords

    return words


def get_spacy_model(model_name: str = "en_core_web_sm"):
    """Lazily load and cache the spaCy English language model.

    Args:
        model_name (str): Name of the spaCy model package.

    Returns:
        spacy.Language: Loaded spaCy NLP pipeline.

    Raises:
        MissingNLPResourceError: If the requested spaCy model is not installed.
    """
    global _spacy_model, _cached_spacy_models
    if model_name in _cached_spacy_models:
        return _cached_spacy_models[model_name]

    import spacy

    if not spacy.util.is_package(model_name):
        raise MissingNLPResourceError(
            f"spaCy model '{model_name}' is not installed.\n"
            f"Please install it using:\n"
            f"    python -m spacy download {model_name}"
        )

    try:
        # Load with parser and NER disabled for high-speed preprocessing
        model = spacy.load(model_name, disable=["ner"])
        _cached_spacy_models[model_name] = model
        _spacy_model = model
        return model
    except Exception as exc:
        raise MissingNLPResourceError(
            f"Failed to load spaCy model '{model_name}': {exc}"
        ) from exc


if __name__ == "__main__":
    if "--download" in sys.argv or "-d" in sys.argv:
        print("Downloading required NLTK resources...")
        download_nltk_resources(quiet=False)
        print("NLTK resources setup complete.")
    else:
        print("NLTK resource availability:")
        for res, avail in check_nltk_resources().items():
            print(f"  - {res}: {'Available' if avail else 'MISSING'}")
        print("\nTo download missing resources, run: python -m app.nlp.resources --download")
