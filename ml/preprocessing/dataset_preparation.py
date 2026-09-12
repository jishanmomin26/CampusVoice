"""Dataset Preparation and Transformation Pipeline for CampusVoice.

Transforms raw wide-format student feedback data into standardized long-format,
applies NLP preprocessing, and prepares reproducible train/test splits.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sklearn.model_selection import train_test_split

# Ensure backend directory is in sys.path so we can reuse Step 3 NLP preprocessing
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.nlp.preprocessing import preprocess_text

# Standard category pairings by fixed column positions in finalDataset0.2.xlsx
CATEGORY_COLUMN_PAIRS: List[Tuple[int, int, str]] = [
    (0, 1, "Teaching"),
    (2, 3, "Course Content"),
    (4, 5, "Examination"),
    (6, 7, "Lab Work"),
    (8, 9, "Library Facilities"),
    (10, 11, "Extracurricular"),
]

# Human-readable sentiment mapping
SENTIMENT_LABEL_MAP: Dict[int, str] = {
    -1: "negative",
    0: "neutral",
    1: "positive",
}


def load_raw_dataset(filepath: str | Path) -> pd.DataFrame:
    """Loads and validates the raw Excel dataset.

    Args:
        filepath: Path to the Excel workbook.

    Returns:
        pd.DataFrame: Loaded raw DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the workbook does not contain exactly 12 columns.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Source dataset not found at: {path}")

    df = pd.read_excel(path, engine="openpyxl")
    if df.shape[1] != 12:
        raise ValueError(
            f"Invalid workbook format: expected exactly 12 columns, found {df.shape[1]}."
        )
    return df


def transform_wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms the wide-format dataset into a normalized long-format DataFrame.

    Each row in the wide dataset contains 6 category text/sentiment pairs.
    This unpivots them into individual feedback records.

    Args:
        df: Raw wide DataFrame (185 rows × 12 columns).

    Returns:
        pd.DataFrame: Long-format DataFrame with columns:
                      ['category', 'sentiment_raw', 'feedback_text_raw']
    """
    records: List[Dict[str, Any]] = []

    for row_idx, row in df.iterrows():
        for s_idx, t_idx, cat_name in CATEGORY_COLUMN_PAIRS:
            raw_sentiment = row.iloc[s_idx]
            raw_text = row.iloc[t_idx]

            records.append({
                "original_row_idx": int(row_idx) + 2,  # 1-indexed accounting for header row
                "category": cat_name,
                "sentiment_raw": raw_sentiment,
                "feedback_text_raw": raw_text,
            })

    return pd.DataFrame(records)


def validate_and_clean_dataset(df_long: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validates records, handles missing/invalid values, and deduplicates within category.

    Validation Rules:
    1. feedback_text must not be empty or whitespace-only.
    2. sentiment must be valid integer in {-1, 0, 1}.
    3. Deduplication is category-aware: identical feedback in different
       categories is legitimately retained.

    Args:
        df_long: Uncleaned long DataFrame.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: (Cleaned DataFrame, Audit metrics dict).
    """
    total_unpivoted = len(df_long)
    audit: Dict[str, Any] = {
        "total_unpivoted_records": total_unpivoted,
        "removed_empty_text": 0,
        "removed_invalid_sentiment": 0,
        "removed_duplicates": 0,
        "final_valid_records": 0,
    }

    # Step 1: Clean and validate feedback text
    cleaned_rows: List[Dict[str, Any]] = []
    for _, row in df_long.iterrows():
        text_val = row["feedback_text_raw"]
        if pd.isna(text_val):
            audit["removed_empty_text"] += 1
            continue

        text_str = str(text_val).strip()
        if not text_str:
            audit["removed_empty_text"] += 1
            continue

        # Step 2: Validate sentiment
        sent_val = row["sentiment_raw"]
        if pd.isna(sent_val):
            audit["removed_invalid_sentiment"] += 1
            continue

        try:
            sent_int = int(float(sent_val))
        except (ValueError, TypeError):
            audit["removed_invalid_sentiment"] += 1
            continue

        if sent_int not in (-1, 0, 1):
            audit["removed_invalid_sentiment"] += 1
            continue

        cleaned_rows.append({
            "category": row["category"],
            "sentiment": sent_int,
            "sentiment_label": SENTIMENT_LABEL_MAP[sent_int],
            "feedback_text": text_str,
        })

    clean_df = pd.DataFrame(cleaned_rows)

    # Step 3: Category-aware deduplication
    before_dedup = len(clean_df)
    clean_df = clean_df.drop_duplicates(subset=["category", "feedback_text"], keep="first").copy()
    duplicates_removed = before_dedup - len(clean_df)
    audit["removed_duplicates"] = int(duplicates_removed)

    # Step 4: Assign unique sequential integer ID
    clean_df.reset_index(drop=True, inplace=True)
    clean_df.insert(0, "id", range(1, len(clean_df) + 1))
    audit["final_valid_records"] = len(clean_df)

    return clean_df, audit


def apply_nlp_preprocessing_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies Step 3 NLP preprocessing pipeline to generate clean_text.

    Args:
        df: Cleaned feedback DataFrame with 'feedback_text' column.

    Returns:
        pd.DataFrame: DataFrame with added 'clean_text' column.
    """
    df = df.copy()
    clean_texts: List[str] = []

    for text in df["feedback_text"]:
        res = preprocess_text(text)
        clean_texts.append(res.clean_text)

    df["clean_text"] = clean_texts
    return df


def split_dataset(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits dataset into stratified train and test sets based on sentiment.

    Args:
        df: Fully preprocessed DataFrame.
        test_size: Proportion for test split (default: 0.2 -> 20%).
        random_state: Random seed for reproducibility (default: 42).

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (train_df, test_df)
    """
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df["sentiment"],
    )

    train_df = train_df.sort_values("id").reset_index(drop=True)
    test_df = test_df.sort_values("id").reset_index(drop=True)
    return train_df, test_df
