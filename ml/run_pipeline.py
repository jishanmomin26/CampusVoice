"""Master Execution Script for Step 4: Dataset Preparation + TF-IDF Feature Engineering.

Executes end-to-end dataset transformation, NLP preprocessing, stratified splitting,
leakage-free TF-IDF vectorization, and artifact serialization.
"""

import json
import os
import sys
from pathlib import Path

# Add backend and ml to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from preprocessing.dataset_preparation import (
    apply_nlp_preprocessing_to_dataframe,
    load_raw_dataset,
    split_dataset,
    transform_wide_to_long,
    validate_and_clean_dataset,
)
from preprocessing.inspect_dataset import inspect_raw_dataset
from preprocessing.tfidf_features import (
    create_tfidf_vectorizer,
    fit_and_transform_features,
    save_vectorizer,
)


def run_step_4_pipeline(
    raw_dataset_path: Path | None = None,
    random_state: int = 42,
    test_size: float = 0.2,
) -> dict:
    """Executes the complete Step 4 dataset pipeline."""
    if raw_dataset_path is None:
        raw_dataset_path = ML_DIR / "datasets" / "finalDataset0.2.xlsx"

    print("=" * 70)
    print("CAMPUSVOICE — STEP 4: DATASET PREPARATION & TF-IDF PIPELINE")
    print("=" * 70)

    # 1. Inspect Raw Workbook
    print("\n[1/6] Inspecting Raw Excel Workbook...")
    raw_inspection = inspect_raw_dataset(raw_dataset_path)

    # 2. Load & Transform Wide -> Long
    print("\n[2/6] Transforming WIDE format to LONG format...")
    raw_df = load_raw_dataset(raw_dataset_path)
    df_long = transform_wide_to_long(raw_df)
    print(f"  Unpivoted records generated: {len(df_long)}")

    # 3. Clean & Validate
    print("\n[3/6] Cleaning, validating, and category-aware deduplication...")
    cleaned_df, audit_metrics = validate_and_clean_dataset(df_long)
    print(f"  Empty feedback removed: {audit_metrics['removed_empty_text']}")
    print(f"  Invalid sentiments removed: {audit_metrics['removed_invalid_sentiment']}")
    print(f"  Category duplicates removed: {audit_metrics['removed_duplicates']}")
    print(f"  Final clean records: {audit_metrics['final_valid_records']}")

    # 4. Apply Step 3 NLP Preprocessing
    print("\n[4/6] Applying Step 3 NLP Preprocessing (lemmatization & negation preservation)...")
    preprocessed_df = apply_nlp_preprocessing_to_dataframe(cleaned_df)
    print(f"  clean_text column populated for {len(preprocessed_df)} records.")

    # 5. Stratified Train / Test Split
    print("\n[5/6] Performing Stratified 80/20 Train/Test Split (random_state=42)...")
    train_df, test_df = split_dataset(
        preprocessed_df, test_size=test_size, random_state=random_state
    )
    print(f"  Training samples: {len(train_df)} ({len(train_df)/len(preprocessed_df)*100:.1f}%)")
    print(f"  Testing samples:  {len(test_df)} ({len(test_df)/len(preprocessed_df)*100:.1f}%)")

    # 6. TF-IDF Feature Extraction (No Leakage!)
    print("\n[6/6] Fitting TF-IDF Vectorizer (Training Split Only)...")
    vectorizer = create_tfidf_vectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    X_train, X_test, tfidf_meta = fit_and_transform_features(
        vectorizer=vectorizer,
        train_texts=train_df["clean_text"],
        test_texts=test_df["clean_text"],
    )
    print(f"  Vocabulary / Feature Count: {tfidf_meta['total_features']}")
    print(f"  X_train matrix shape: {X_train.shape}")
    print(f"  X_test matrix shape:  {X_test.shape}")

    # 7. Save Artifacts
    print("\nSaving generated datasets and models...")
    datasets_dir = ML_DIR / "datasets"
    models_dir = ML_DIR / "models"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    processed_path = datasets_dir / "processed_feedback.csv"
    train_path = datasets_dir / "train_feedback.csv"
    test_path = datasets_dir / "test_feedback.csv"
    summary_path = datasets_dir / "dataset_summary.json"
    vectorizer_path = models_dir / "tfidf_vectorizer.joblib"

    preprocessed_df.to_csv(processed_path, index=False)
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    save_vectorizer(vectorizer, vectorizer_path)

    # Compile comprehensive summary report
    summary: dict = {
        "raw_dataset": {
            "filename": raw_dataset_path.name,
            "rows": raw_inspection["total_rows"],
            "columns": raw_inspection["total_columns"],
        },
        "transformation": {
            "unpivoted_records": audit_metrics["total_unpivoted_records"],
            "removed_empty_text": audit_metrics["removed_empty_text"],
            "removed_invalid_sentiment": audit_metrics["removed_invalid_sentiment"],
            "removed_duplicates": audit_metrics["removed_duplicates"],
            "final_clean_records": audit_metrics["final_valid_records"],
        },
        "distributions": {
            "category": preprocessed_df["category"].value_counts().to_dict(),
            "sentiment": {
                str(k): int(v)
                for k, v in preprocessed_df["sentiment"].value_counts().to_dict().items()
            },
            "sentiment_label": preprocessed_df["sentiment_label"].value_counts().to_dict(),
            "train_sentiment": {
                str(k): int(v)
                for k, v in train_df["sentiment"].value_counts().to_dict().items()
            },
            "test_sentiment": {
                str(k): int(v)
                for k, v in test_df["sentiment"].value_counts().to_dict().items()
            },
        },
        "splits": {
            "train_count": len(train_df),
            "test_count": len(test_df),
            "train_ratio": 1.0 - test_size,
            "test_ratio": test_size,
            "random_state": random_state,
        },
        "tfidf_features": {
            "total_features": tfidf_meta["total_features"],
            "train_matrix_shape": list(tfidf_meta["train_matrix_shape"]),
            "test_matrix_shape": list(tfidf_meta["test_matrix_shape"]),
            "configuration": {
                "ngram_range": list(vectorizer.ngram_range),
                "min_df": vectorizer.min_df,
                "max_df": vectorizer.max_df,
                "sublinear_tf": vectorizer.sublinear_tf,
            },
            "sample_features": tfidf_meta["sample_features"],
        },
        "artifacts": {
            "processed_dataset": str(processed_path.relative_to(BASE_DIR)),
            "train_dataset": str(train_path.relative_to(BASE_DIR)),
            "test_dataset": str(test_path.relative_to(BASE_DIR)),
            "tfidf_vectorizer": str(vectorizer_path.relative_to(BASE_DIR)),
            "summary_file": str(summary_path.relative_to(BASE_DIR)),
        },
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"  Saved: {processed_path.name}")
    print(f"  Saved: {train_path.name}")
    print(f"  Saved: {test_path.name}")
    print(f"  Saved: {summary_path.name}")
    print(f"  Saved: {vectorizer_path.name}")

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")

    return summary


if __name__ == "__main__":
    run_step_4_pipeline()
