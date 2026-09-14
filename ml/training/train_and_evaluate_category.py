"""Master Execution Pipeline for Feedback Category Classification (Step 6).

Coordinates:
  1. Dataset loading and canonical category validation
  2. TF-IDF feature transformation (reusing Step 4 fitted vectorizer)
  3. Training Logistic Regression & Multinomial Naive Bayes models
  4. Evaluating both models strictly on held-out test data
  5. Generating 6x6 confusion matrix plots via pure matplotlib
  6. Selecting best model via Macro F1
  7. Persisting all model and evaluation artifacts
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Dict, Any
import joblib
import numpy as np

# Ensure project base directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.evaluation.evaluate_category_models import (
    CANONICAL_CATEGORIES,
    compare_and_select_best_category_model,
    evaluate_category_model,
    export_category_evaluation_artifacts,
    plot_category_confusion_matrix,
)
from ml.training.train_category_models import (
    load_category_data,
    load_tfidf_vectorizer,
    prepare_category_features,
    save_category_models,
    train_category_models,
)


def run_category_training_pipeline(
    data_dir: Path | None = None,
    models_dir: Path | None = None,
    eval_dir: Path | None = None,
) -> Dict[str, Any]:
    """Executes the complete Step 6 training, evaluation, and serialization pipeline."""
    if data_dir is None:
        data_dir = BASE_DIR / "ml" / "datasets"
    if models_dir is None:
        models_dir = BASE_DIR / "ml" / "models"
    if eval_dir is None:
        eval_dir = BASE_DIR / "ml" / "evaluation"

    plots_dir = eval_dir / "results"
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("CAMPUSVOICE - STEP 6: FEEDBACK CATEGORY CLASSIFICATION PIPELINE")
    print("=" * 80)

    # 1. Load Data & Validate
    print("\n[1/6] Loading category datasets and validating canonical categories...")
    train_df, test_df = load_category_data(data_dir=data_dir)
    print(f"  Training set: {len(train_df)} samples")
    print(f"  Testing set:  {len(test_df)} samples")
    print(f"  Canonical categories ({len(CANONICAL_CATEGORIES)}): {', '.join(CANONICAL_CATEGORIES)}")

    # 2. Load Step 4 TF-IDF Vectorizer
    print("\n[2/6] Loading existing Step 4 TF-IDF vectorizer artifact...")
    vectorizer = load_tfidf_vectorizer(model_dir=models_dir)
    vocab_size = len(vectorizer.vocabulary_)
    print(f"  Loaded vectorizer vocabulary size: {vocab_size} features (NO refitting)")

    # 3. Transform Text Features
    print("\n[3/6] Transforming text to TF-IDF feature matrices...")
    X_train, y_train, X_test, y_test = prepare_category_features(train_df, test_df, vectorizer)
    print(f"  X_train shape: {X_train.shape}")
    print(f"  X_test shape:  {X_test.shape}")

    # 4. Train Candidate Models
    print("\n[4/6] Training category classification models...")
    print("  - Training Logistic Regression (max_iter=2000, random_state=42)...")
    print("  - Training Multinomial Naive Bayes (alpha=1.0)...")
    models = train_category_models(X_train, y_train)

    # Save individual models
    saved_model_paths = save_category_models(models, output_dir=models_dir)
    for model_name, path in saved_model_paths.items():
        print(f"  Saved {model_name} -> {path.name}")

    # 5. Evaluate on Held-Out Test Set & Plot Confusion Matrices
    print(f"\n[5/6] Evaluating models strictly on held-out test data ({len(y_test)} samples)...")
    eval_results = {}
    for model_name, model_obj in models.items():
        metrics = evaluate_category_model(model_obj, X_test, y_test, CANONICAL_CATEGORIES)
        eval_results[model_name] = metrics

        # Generate 6x6 confusion matrix plot
        cm_array = np.array(metrics["confusion_matrix"]["matrix"])
        plot_filename_map = {
            "logistic_regression": "category_logistic_regression_confusion_matrix.png",
            "multinomial_nb": "category_naive_bayes_confusion_matrix.png",
        }
        plot_filename = plot_filename_map.get(model_name, f"category_{model_name}_confusion_matrix.png")
        plot_path = plots_dir / plot_filename
        plot_title = (
            f"Category Confusion Matrix: {model_name.replace('_', ' ').title()}\n"
            f"(Accuracy: {metrics['accuracy']:.2%}, Macro F1: {metrics['f1_macro']:.4f})"
        )
        plot_category_confusion_matrix(cm_array, CANONICAL_CATEGORIES, plot_title, plot_path)
        print(f"  Generated confusion matrix plot: {plot_path.name}")

    # Compare models using Macro F1
    comparison = compare_and_select_best_category_model(eval_results)
    best_name = comparison["best_model"]
    best_model_obj = models[best_name]
    best_f1 = comparison["best_macro_f1"]

    print(f"\n  BEST MODEL SELECTED: {best_name.upper()} (Macro F1: {best_f1:.4f})")

    # Save best model
    best_model_path = models_dir / "best_category_model.joblib"
    joblib.dump(best_model_obj, best_model_path)
    print(f"  Saved best model -> {best_model_path.name}")

    # 6. Export Metadata & Evaluation Artifacts
    print("\n[6/6] Persisting evaluation metrics, comparison report, and model metadata...")

    # Export comparison JSON and readable text report
    json_path, txt_path = export_category_evaluation_artifacts(
        eval_results, comparison, eval_dir=eval_dir
    )
    print(f"  Saved: {json_path.name}")
    print(f"  Saved: {txt_path.name}")

    # Save category_model_metadata.json
    best_hyperparams = {}
    if best_name == "logistic_regression":
        best_hyperparams = {"max_iter": 2000, "random_state": 42, "class_weight": None}
    elif best_name == "multinomial_nb":
        best_hyperparams = {"alpha": 1.0}

    metadata_payload = {
        "selected_model": best_name,
        "selection_metric": "f1_macro",
        "best_macro_f1": best_f1,
        "model_hyperparameters": best_hyperparams,
        "training_sample_count": int(len(train_df)),
        "test_sample_count": int(len(test_df)),
        "tfidf_feature_count": int(vocab_size),
        "category_names": CANONICAL_CATEGORIES,
        "evaluation_metrics": eval_results[best_name],
        "all_models_summary": comparison["models"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = models_dir / "category_model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)
    print(f"  Saved: {metadata_path.name}")

    # Print Summary Table
    print("\n" + "=" * 80)
    print("CATEGORY CLASSIFICATION PERFORMANCE COMPARISON (HELD-OUT TEST SET)")
    print("=" * 80)
    header = f"{'Metric':<24} | {'Logistic Regression':<22} | {'Multinomial Naive Bayes':<24}"
    print(header)
    print("-" * len(header))
    metrics_display = [
        ("Accuracy", "accuracy"),
        ("Precision (Macro)", "precision_macro"),
        ("Recall (Macro)", "recall_macro"),
        ("F1-Score (Macro)", "f1_macro"),
        ("Precision (Weighted)", "precision_weighted"),
        ("Recall (Weighted)", "recall_weighted"),
        ("F1-Score (Weighted)", "f1_weighted"),
    ]
    for label, key in metrics_display:
        lr_val = eval_results["logistic_regression"][key]
        nb_val = eval_results["multinomial_nb"][key]
        print(f"{label:<24} | {lr_val:<22.4f} | {nb_val:<24.4f}")
    print("=" * 80)

    return {
        "best_model": best_name,
        "best_macro_f1": best_f1,
        "evaluation_results": eval_results,
        "comparison": comparison,
    }


if __name__ == "__main__":
    run_category_training_pipeline()
