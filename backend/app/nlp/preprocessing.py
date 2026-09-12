"""NLP Preprocessing Pipeline for Student Feedback."""

import re
import unicodedata
from typing import List, Optional, Set

from app.nlp.resources import (
    SENTIMENT_NEGATION_WORDS,
    get_spacy_model,
    get_stopwords,
)
from app.schemas.nlp import PreprocessingResult


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping whitespace, and normalizing Unicode.

    Args:
        text (str): Raw input text.

    Returns:
        str: Cleaned and normalized text string.
    """
    if not text:
        return ""

    # Normalize Unicode characters (NFKD decomposition then ASCII/compatibility normalization)
    normalized = unicodedata.normalize("NFKD", text)

    # Convert to lowercase
    normalized = normalized.lower()

    # Normalize excessive whitespace (spaces, tabs, newlines -> single space)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Remove unprintable/control characters while keeping standard text characters
    normalized = "".join(
        ch for ch in normalized if unicodedata.category(ch)[0] != "C"
    )

    return normalized


def tokenize_text(text: str) -> List[str]:
    """Tokenize normalized text into linguistic word tokens using spaCy.

    Args:
        text (str): Input text to tokenize.

    Returns:
        List[str]: Extracted word tokens.
    """
    normalized = normalize_text(text)
    if not normalized:
        return []

    nlp = get_spacy_model()
    doc = nlp(normalized)

    # Filter out standalone punctuation and whitespace tokens
    tokens = [
        token.text
        for token in doc
        if not token.is_punct and not token.is_space and token.text.strip()
    ]
    return tokens


def preprocess_text(
    text: str,
    custom_stopwords: Optional[Set[str]] = None,
    preserve_negations: bool = True,
) -> PreprocessingResult:
    """Execute the full NLP preprocessing pipeline on student feedback text.

    Pipeline:
        Raw Text
          ↓
        Normalize (lowercase, trim, collapse whitespace)
          ↓
        Linguistic Tokenization & Lemmatization (spaCy)
          ↓
        Stopword Removal (NLTK, with sentiment negation words preserved)
          ↓
        Lemmatized Clean Text for ML models

    Args:
        text (str): Raw student feedback text.
        custom_stopwords (Optional[Set[str]]): Additional stopwords to exclude.
        preserve_negations (bool): If True, retains critical sentiment words ('not', 'no', 'never').

    Returns:
        PreprocessingResult: Structured object containing all intermediate and final text representations.
    """
    normalized = normalize_text(text)

    # Handle empty or whitespace-only inputs gracefully
    if not normalized:
        return PreprocessingResult(
            original_text=text,
            normalized_text="",
            tokens=[],
            filtered_tokens=[],
            lemmatized_tokens=[],
            clean_text="",
        )

    # Obtain stopwords with negation preservation
    stopwords_set = get_stopwords(
        preserve_negations=preserve_negations,
        custom_stopwords=custom_stopwords,
    )

    nlp = get_spacy_model()
    doc = nlp(normalized)

    raw_tokens: List[str] = []
    filtered_tokens: List[str] = []
    lemmatized_tokens: List[str] = []

    for token in doc:
        # Skip pure punctuation, brackets, quotes, and whitespace
        if token.is_punct or token.is_space or not token.text.strip():
            continue

        token_text = token.text.lower()
        raw_tokens.append(token_text)

        # Handle contractions like "n't" -> treat as negation "not"
        is_negation = token_text in SENTIMENT_NEGATION_WORDS or token_text == "n't"

        # Check stopword membership (negations are explicitly exempted)
        if not is_negation and token_text in stopwords_set:
            continue

        # Standardize "n't" token representation to "not" for consistency
        normalized_token_word = "not" if token_text == "n't" else token_text
        filtered_tokens.append(normalized_token_word)

        # Extract lemmatized representation
        if is_negation:
            lemma = "not" if token_text in ("n't", "not") else token_text
        else:
            lemma = token.lemma_.lower().strip()
            # If spaCy returns older placeholder "-PRON-" or empty lemma, fallback to token text
            if lemma in ("-pron-", ""):
                lemma = token_text

        lemmatized_tokens.append(lemma)

    clean_text = " ".join(lemmatized_tokens)

    return PreprocessingResult(
        original_text=text,
        normalized_text=normalized,
        tokens=raw_tokens,
        filtered_tokens=filtered_tokens,
        lemmatized_tokens=lemmatized_tokens,
        clean_text=clean_text,
    )
