"""Dataset Inspection Utility for CampusVoice.

Inspects the original student feedback workbook (finalDataset0.2.xlsx)
without modifying or altering the original file.
"""

import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd

# Expected category column pairs in the raw workbook
EXPECTED_CATEGORY_PAIRS = [
    (0, 1, "Teaching"),
    (2, 3, "Course Content"),
    (4, 5, "Examination"),
    (6, 7, "Lab Work"),
    (8, 9, "Library Facilities"),
    (10, 11, "Extracurricular"),
]


def inspect_raw_dataset(filepath: str | Path) -> Dict[str, Any]:
    """Inspects the raw Excel workbook and produces a diagnostic summary.

    Args:
        filepath: Path to the raw Excel dataset.

    Returns:
        Dict[str, Any]: Structural metrics and value distributions.

    Raises:
        FileNotFoundError: If the Excel file does not exist.
        ValueError: If column count does not match the required 12 columns.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {path}")

    # Read the raw Excel workbook
    df = pd.read_excel(path, engine="openpyxl")
    num_rows, num_cols = df.shape

    # Strict validation of column count
    if num_cols != 12:
        raise ValueError(
            f"Invalid dataset structure: Expected exactly 12 columns, but found {num_cols}."
        )

    raw_col_names = [str(c) for c in df.columns]

    inspection_results: Dict[str, Any] = {
        "file_name": path.name,
        "total_rows": int(num_rows),
        "total_columns": int(num_cols),
        "column_names": raw_col_names,
        "raw_duplicate_rows": int(df.duplicated().sum()),
        "categories": {},
    }

    print("\n" + "=" * 60)
    print("CAMPUSVOICE DATASET INSPECTION REPORT")
    print("=" * 60)
    print(f"File: {path.name}")
    print(f"Total Rows: {num_rows}")
    print(f"Total Columns: {num_cols}")
    print(f"Raw Full-Row Duplicates: {inspection_results['raw_duplicate_rows']}\n")
    print("Columns in Workbook:")
    for idx, col in enumerate(raw_col_names):
        print(f"  Col {idx:02d}: {repr(col)}")

    print("\n" + "-" * 60)
    print("CATEGORY COLUMN PAIRINGS & DISTRIBUTIONS:")
    print("-" * 60)

    for s_idx, t_idx, cat_name in EXPECTED_CATEGORY_PAIRS:
        sent_col = df.iloc[:, s_idx]
        text_col = df.iloc[:, t_idx]

        # Calculate missing / blank text feedback cells
        is_blank_text = text_col.isna() | (text_col.astype(str).str.strip() == "")
        blank_text_count = int(is_blank_text.sum())

        # Distribution of sentiments
        sent_counts = sent_col.value_counts(dropna=False).to_dict()
        sent_counts_clean = {str(k): int(v) for k, v in sent_counts.items()}

        unique_sents = sorted([str(s) for s in sent_col.dropna().unique()])

        inspection_results["categories"][cat_name] = {
            "sentiment_col_idx": s_idx,
            "sentiment_col_name": raw_col_names[s_idx],
            "text_col_idx": t_idx,
            "text_col_name": raw_col_names[t_idx],
            "total_records": len(df),
            "blank_feedback_count": blank_text_count,
            "sentiment_distribution": sent_counts_clean,
            "unique_sentiments": unique_sents,
        }

        print(f"[{cat_name}]")
        print(f"  Sentiment Col ({s_idx}): {repr(raw_col_names[s_idx])} -> Values: {sent_counts_clean}")
        print(f"  Text Col ({t_idx}): {repr(raw_col_names[t_idx])} -> Blank/Missing: {blank_text_count}")

    print("=" * 60 + "\n")
    return inspection_results


if __name__ == "__main__":
    import sys

    default_path = Path(__file__).resolve().parent.parent / "datasets" / "finalDataset0.2.xlsx"
    target_path = sys.argv[1] if len(sys.argv) > 1 else default_path
    inspect_raw_dataset(target_path)
