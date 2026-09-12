"""Model Training Module for CampusVoice.

Trains Logistic Regression and Multinomial Naive Bayes models on pre-extracted
TF-IDF features from the training dataset.
"""

from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import pandas as pd
from scipy.sparse import spmatrix
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
MODELS_DIR = BASE_DIR / "models"


def load_training_data(
    train_path: str | Path | None = None,
    test_path: str | Path | None = None,
    vectorizer_path: str | Path | None = None,
) -> Tuple[spmatrix, spmatrix, pd.Series, pd.Series, TfidfVectorizer]:
    """Loads train/test datasets and transforms clean text using the existing fitted TF-IDF vectorizer.

    Args:
        train_path: Path to train_feedback.csv.
        test_path: Path to test_feedback.csv.
        vectorizer_path: Path to tfidf_vectorizer.joblib (must NOT be refit).

    Returns:
        Tuple of (X_train, X_test, y_train, y_test, vectorizer).
    """
    if train_path is None:
        train_path = DATASETS_DIR / "train_feedback.csv"
    if test_path is None:
        test_path = DATASETS_DIR / "test_feedback.csv"
    if vectorizer_path is None:
        vectorizer_path = MODELS_DIR / "tfidf_vectorizer.joblib"

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    # Load existing fitted vectorizer (DO NOT REFIT)
    vectorizer: TfidfVectorizer = joblib.load(vectorizer_path)

    # Transform texts
    X_train = vectorizer.transform(train_df["clean_text"].fillna(""))
    X_test = vectorizer.transform(test_df["clean_text"].fillna(""))

    y_train = train_df["sentiment"].astype(int)
    y_test = test_df["sentiment"].astype(int)

    return X_train, X_test, y_train, y_test, vectorizer


def train_logistic_regression(
    X_train: spmatrix,
    y_train: pd.Series,
    max_iter: int = 2000,
    random_state: int = 42,
    class_weight: str | None = "balanced",
) -> LogisticRegression:
    """Trains a Logistic Regression classifier on TF-IDF features.

    Args:
        X_train: Sparse TF-IDF feature matrix.
        y_train: Target sentiment series.
        max_iter: Maximum solver iterations (default: 2000).
        random_state: Random seed for reproducibility (default: 42).
        class_weight: Class balancing strategy (default: "balanced").

    Returns:
        LogisticRegression: Fitted model.
    """
    model = LogisticRegression(
        max_iter=max_iter,
        random_state=random_state,
        class_weight=class_weight,
    )
    model.fit(X_train, y_train)
    return model


def train_multinomial_nb(
    X_train: spmatrix,
    y_train: pd.Series,
    alpha: float = 1.0,
) -> MultinomialNB:
    """Trains a Multinomial Naive Bayes classifier on TF-IDF features.

    Args:
        X_train: Sparse TF-IDF feature matrix.
        y_train: Target sentiment series.
        alpha: Additive (Laplace) smoothing parameter (default: 1.0).

    Returns:
        MultinomialNB: Fitted model.
    """
    model = MultinomialNB(alpha=alpha)
    model.fit(X_train, y_train)
    return model


def train_all_models(
    X_train: spmatrix,
    y_train: pd.Series,
) -> Dict[str, Any]:
    """Trains both Logistic Regression and Multinomial Naive Bayes.

    Returns:
        Dict[str, Any]: Mapping of model name to fitted estimator instance.
    """
    lr_model = train_logistic_regression(X_train, y_train)
    nb_model = train_multinomial_nb(X_train, y_train)

    return {
        "logistic_regression": lr_model,
        "multinomial_nb": nb_model,
    }
