"""Feedback Category Classification - Model Training Module.

Trains Logistic Regression and Multinomial Naive Bayes models to classify
student feedback comments into 6 canonical categories:
  - Teaching
  - Course Content
  - Examination
  - Lab Work
  - Library Facilities
  - Extracurricular

Strictly reuses the pre-fitted Step 4 TF-IDF vectorizer without refitting.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

# Add project base directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Canonical categories in alphabetical order for stable matrix indexing
CANONICAL_CATEGORIES: List[str] = [
    "Course Content",
    "Examination",
    "Extracurricular",
    "Lab Work",
    "Library Facilities",
    "Teaching",
]

REQUIRED_COLUMNS = {"clean_text", "category"}


def validate_category_data(df: pd.DataFrame, dataset_name: str = "dataset") -> None:
    """Validates required columns and canonical categories in dataset.

    Args:
        df: DataFrame to validate.
        dataset_name: Human-readable name for error messages.

    Raises:
        ValueError: If required columns or canonical categories are invalid.
    """
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"{dataset_name} missing required columns: {sorted(missing_cols)}"
        )

    # Check for missing clean_text
    if df["clean_text"].isnull().any():
        raise ValueError(f"{dataset_name} contains null values in 'clean_text'")

    # Validate categories against canonical set
    found_categories = set(df["category"].dropna().unique())
    canonical_set = set(CANONICAL_CATEGORIES)

    unexpected = found_categories - canonical_set
    if unexpected:
        raise ValueError(
            f"{dataset_name} contains unexpected category labels: {sorted(unexpected)}. "
            f"Expected only: {sorted(canonical_set)}"
        )

    missing_categories = canonical_set - found_categories
    if missing_categories:
        raise ValueError(
            f"{dataset_name} missing expected canonical categories: {sorted(missing_categories)}"
        )


def load_category_data(
    data_dir: Path | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Loads and validates train and test category datasets.

    Args:
        data_dir: Directory containing train_feedback.csv and test_feedback.csv.

    Returns:
        Tuple of (train_df, test_df).
    """
    if data_dir is None:
        data_dir = BASE_DIR / "ml" / "datasets"

    train_path = data_dir / "train_feedback.csv"
    test_path = data_dir / "test_feedback.csv"

    if not train_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Testing dataset not found: {test_path}")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    validate_category_data(train_df, "Training dataset (train_feedback.csv)")
    validate_category_data(test_df, "Testing dataset (test_feedback.csv)")

    return train_df, test_df


def load_tfidf_vectorizer(model_dir: Path | None = None):
    """Loads the pre-fitted Step 4 TF-IDF vectorizer artifact.

    Args:
        model_dir: Directory containing tfidf_vectorizer.joblib.

    Returns:
        Fitted scikit-learn TfidfVectorizer.

    Raises:
        FileNotFoundError: If the vectorizer artifact does not exist.
    """
    if model_dir is None:
        model_dir = BASE_DIR / "ml" / "models"

    vectorizer_path = model_dir / "tfidf_vectorizer.joblib"
    if not vectorizer_path.exists():
        raise FileNotFoundError(
            f"TF-IDF vectorizer artifact not found: {vectorizer_path}. "
            "Please run Step 4 (ml/run_pipeline.py) first."
        )

    return joblib.load(vectorizer_path)


def prepare_category_features(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    vectorizer,
) -> Tuple:
    """Transforms clean_text columns using existing fitted TF-IDF vectorizer.

    Args:
        train_df: Training DataFrame.
        test_df: Testing DataFrame.
        vectorizer: Fitted TF-IDF vectorizer (Step 4 artifact).

    Returns:
        Tuple of (X_train, y_train, X_test, y_test).
    """
    # Use clean_text as input features
    X_train = vectorizer.transform(train_df["clean_text"].astype(str))
    y_train = train_df["category"].values

    X_test = vectorizer.transform(test_df["clean_text"].astype(str))
    y_test = test_df["category"].values

    return X_train, y_train, X_test, y_test


def train_logistic_regression(X_train, y_train) -> LogisticRegression:
    """Trains Logistic Regression classifier for category classification.

    Configuration:
      - max_iter: 2000
      - random_state: 42
      - class_weight: None (categories are already reasonably balanced)
    """
    model = LogisticRegression(
        max_iter=2000,
        random_state=42,
        class_weight=None,
    )
    model.fit(X_train, y_train)
    return model


def train_multinomial_nb(X_train, y_train) -> MultinomialNB:
    """Trains Multinomial Naive Bayes classifier for category classification.

    Configuration:
      - alpha: 1.0 (Laplace smoothing)
    """
    model = MultinomialNB(alpha=1.0)
    model.fit(X_train, y_train)
    return model


def train_category_models(X_train, y_train) -> Dict[str, object]:
    """Trains both Logistic Regression and MultinomialNB models.

    Args:
        X_train: Feature matrix.
        y_train: Category target labels.

    Returns:
        Dictionary mapping model names to fitted model instances.
    """
    lr_model = train_logistic_regression(X_train, y_train)
    nb_model = train_multinomial_nb(X_train, y_train)

    return {
        "logistic_regression": lr_model,
        "multinomial_nb": nb_model,
    }


def save_category_models(
    models_dict: Dict[str, object],
    output_dir: Path | None = None,
) -> Dict[str, Path]:
    """Saves trained individual category models to disk.

    Args:
        models_dict: Mapping of model names to model instances.
        output_dir: Destination directory.

    Returns:
        Mapping of model names to saved file paths.
    """
    if output_dir is None:
        output_dir = BASE_DIR / "ml" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_mapping = {
        "logistic_regression": "logistic_regression_category.joblib",
        "multinomial_nb": "naive_bayes_category.joblib",
    }

    saved_paths = {}
    for key, filename in file_mapping.items():
        if key in models_dict:
            target_path = output_dir / filename
            joblib.dump(models_dict[key], target_path)
            saved_paths[key] = target_path

    return saved_paths
