"""TF-IDF Feature Engineering Pipeline for CampusVoice.

Extracts unigram and bigram TF-IDF features strictly on the training split
to completely prevent test-data leakage, and serializes the fitted vectorizer.
"""

from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer


def create_tfidf_vectorizer(
    ngram_range: Tuple[int, int] = (1, 2),
    min_df: int = 1,
    max_df: float = 0.95,
    sublinear_tf: bool = True,
) -> TfidfVectorizer:
    """Instantiates a TfidfVectorizer with validated parameters for student feedback.

    Args:
        ngram_range: Unigram and bigram boundaries (default: (1, 2)).
        min_df: Minimum document frequency threshold (strictly set to 1 for small datasets).
        max_df: Maximum document frequency threshold to filter overly ubiquitous terms (default: 0.95).
        sublinear_tf: Apply sublinear scaling (1 + log(tf)) to dampen high-frequency term effects.

    Returns:
        TfidfVectorizer: Configured un-fitted vectorizer.
    """
    return TfidfVectorizer(
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=sublinear_tf,
    )


def fit_and_transform_features(
    vectorizer: TfidfVectorizer,
    train_texts: pd.Series | list[str],
    test_texts: pd.Series | list[str],
) -> Tuple[spmatrix, spmatrix, Dict[str, Any]]:
    """Fits vectorizer strictly on training text and transforms test text without leakage.

    Args:
        vectorizer: Configured TfidfVectorizer instance.
        train_texts: Training split cleaned text sequences.
        test_texts: Testing split cleaned text sequences.

    Returns:
        Tuple[spmatrix, spmatrix, Dict[str, Any]]:
            - X_train: Sparse TF-IDF matrix for training data.
            - X_test: Sparse TF-IDF matrix for testing data.
            - metadata: Feature summary (vocab size, matrix shapes).
    """
    # Fit strictly on the training set
    X_train = vectorizer.fit_transform(train_texts)

    # Transform testing set with the training vocabulary
    X_test = vectorizer.transform(test_texts)

    feature_names = vectorizer.get_feature_names_out()

    metadata: Dict[str, Any] = {
        "train_matrix_shape": X_train.shape,
        "test_matrix_shape": X_test.shape,
        "total_features": len(feature_names),
        "ngram_range": vectorizer.ngram_range,
        "min_df": vectorizer.min_df,
        "max_df": vectorizer.max_df,
        "sublinear_tf": vectorizer.sublinear_tf,
        "sample_features": list(feature_names[:15]),
    }

    return X_train, X_test, metadata


def save_vectorizer(vectorizer: TfidfVectorizer, output_path: str | Path) -> Path:
    """Serializes the fitted vectorizer using joblib.

    Args:
        vectorizer: Fitted TfidfVectorizer.
        output_path: Destination filepath.

    Returns:
        Path: Resolved filepath where artifact was saved.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, target)
    return target


def load_vectorizer(filepath: str | Path) -> TfidfVectorizer:
    """Loads a previously serialized vectorizer artifact.

    Args:
        filepath: Path to the .joblib file.

    Returns:
        TfidfVectorizer: Loaded vectorizer ready for inference.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Vectorizer artifact not found: {path}")
    return joblib.load(path)
