"""Master Script for Step 5: Model Training, Evaluation, and Selection.

Trains Logistic Regression and Multinomial Naive Bayes models, evaluates them on
held-out test data, compares their performance, selects the best model by Macro F1,
and persists all model and evaluation artifacts.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from datetime import datetime, timezone
import json
import joblib

from ml.evaluation.evaluate_models import compare_and_select_best_model, evaluate_model
from ml.training.train_models import (
    load_training_data,
    train_logistic_regression,
    train_multinomial_nb,
)

ML_DIR = BASE_DIR / "ml"
MODELS_DIR = ML_DIR / "models"
EVAL_DIR = ML_DIR / "evaluation"


def run_training_and_evaluation() -> dict:
    """Executes the complete model training, evaluation, and selection pipeline."""
    print("=" * 75)
    print("CAMPUSVOICE — STEP 5: MODEL TRAINING & COMPARISON")
    print("=" * 75)

    # 1. Load data and feature matrices
    print("\n[1/5] Loading training and testing datasets with fitted TF-IDF vectorizer...")
    X_train, X_test, y_train, y_test, vectorizer = load_training_data()
    print(f"  Training samples: {X_train.shape[0]}, Features: {X_train.shape[1]}")
    print(f"  Testing samples:  {X_test.shape[0]}, Features: {X_test.shape[1]}")

    # 2. Train Models
    print("\n[2/5] Training classification models...")
    print("  - Training Logistic Regression (max_iter=2000, class_weight='balanced', random_state=42)...")
    lr_model = train_logistic_regression(
        X_train, y_train, max_iter=2000, random_state=42, class_weight="balanced"
    )

    print("  - Training Multinomial Naive Bayes (alpha=1.0)...")
    nb_model = train_multinomial_nb(X_train, y_train, alpha=1.0)

    # 3. Save Both Models
    print("\n[3/5] Saving individual model artifacts...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    lr_path = MODELS_DIR / "logistic_regression_sentiment.joblib"
    nb_path = MODELS_DIR / "naive_bayes_sentiment.joblib"

    joblib.dump(lr_model, lr_path)
    joblib.dump(nb_model, nb_path)
    print(f"  Saved: {lr_path.name}")
    print(f"  Saved: {nb_path.name}")

    # 4. Evaluate Models on Held-Out Test Set
    print("\n[4/5] Evaluating models on held-out test data (145 samples)...")
    lr_eval = evaluate_model(lr_model, X_test, y_test)
    nb_eval = evaluate_model(nb_model, X_test, y_test)

    eval_results = {
        "logistic_regression": lr_eval,
        "multinomial_nb": nb_eval,
    }

    # Model Comparison & Selection by Macro F1
    best_name, comparison = compare_and_select_best_model(eval_results)
    best_model = lr_model if best_name == "logistic_regression" else nb_model

    best_path = MODELS_DIR / "best_sentiment_model.joblib"
    joblib.dump(best_model, best_path)
    print(f"  Best Model Selected: {best_name.upper()} (Macro F1: {comparison['best_macro_f1']:.4f})")
    print(f"  Saved Best Model to: {best_path.name}")

    # 5. Save Evaluation Artifacts
    print("\n[5/5] Persisting evaluation metrics and confusion matrices...")
    comparison_path = EVAL_DIR / "model_comparison.json"
    confusion_path = EVAL_DIR / "confusion_matrix.json"
    metadata_path = MODELS_DIR / "model_metadata.json"

    # Save comparison JSON
    with open(comparison_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    # Save detailed confusion matrices
    confusion_matrices = {
        "logistic_regression": lr_eval["confusion_matrix"],
        "multinomial_nb": nb_eval["confusion_matrix"],
    }
    with open(confusion_path, "w", encoding="utf-8") as f:
        json.dump(confusion_matrices, f, indent=2)

    # Save metadata for the best model
    metadata = {
        "best_model": best_name,
        "selected_metric": "f1_macro",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_samples": int(X_train.shape[0]),
        "testing_samples": int(X_test.shape[0]),
        "total_features": int(X_train.shape[1]),
        "best_model_metrics": eval_results[best_name],
        "all_models_summary": comparison["models"],
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved: {comparison_path.name}")
    print(f"  Saved: {confusion_path.name}")
    print(f"  Saved: {metadata_path.name}")

    # Print Formatted Report Table
    print("\n" + "=" * 75)
    print("MODEL PERFORMANCE COMPARISON (HELD-OUT TEST SET)")
    print("=" * 75)
    print(f"{'Metric':<25} | {'Logistic Regression':<22} | {'Multinomial Naive Bayes':<22}")
    print("-" * 75)
    print(f"{'Accuracy':<25} | {lr_eval['accuracy']:<22.4f} | {nb_eval['accuracy']:<22.4f}")
    print(f"{'Precision (Macro)':<25} | {lr_eval['precision_macro']:<22.4f} | {nb_eval['precision_macro']:<22.4f}")
    print(f"{'Recall (Macro)':<25} | {lr_eval['recall_macro']:<22.4f} | {nb_eval['recall_macro']:<22.4f}")
    print(f"{'F1-Score (Macro)':<25} | {lr_eval['f1_macro']:<22.4f} | {nb_eval['f1_macro']:<22.4f}")
    print(f"{'Precision (Weighted)':<25} | {lr_eval['precision_weighted']:<22.4f} | {nb_eval['precision_weighted']:<22.4f}")
    print(f"{'Recall (Weighted)':<25} | {lr_eval['recall_weighted']:<22.4f} | {nb_eval['recall_weighted']:<22.4f}")
    print(f"{'F1-Score (Weighted)':<25} | {lr_eval['f1_weighted']:<22.4f} | {nb_eval['f1_weighted']:<22.4f}")
    print("=" * 75)

    print("\nCONFUSION MATRIX — LOGISTIC REGRESSION:")
    print("                 Pred Negative | Pred Neutral | Pred Positive")
    cm_lr = lr_eval["confusion_matrix"]["matrix"]
    print(f"Actual Negative:      {cm_lr[0][0]:<8} | {cm_lr[0][1]:<12} | {cm_lr[0][2]:<13}")
    print(f"Actual Neutral:       {cm_lr[1][0]:<8} | {cm_lr[1][1]:<12} | {cm_lr[1][2]:<13}")
    print(f"Actual Positive:      {cm_lr[2][0]:<8} | {cm_lr[2][1]:<12} | {cm_lr[2][2]:<13}")

    print("\nCONFUSION MATRIX — MULTINOMIAL NAIVE BAYES:")
    print("                 Pred Negative | Pred Neutral | Pred Positive")
    cm_nb = nb_eval["confusion_matrix"]["matrix"]
    print(f"Actual Negative:      {cm_nb[0][0]:<8} | {cm_nb[0][1]:<12} | {cm_nb[0][2]:<13}")
    print(f"Actual Neutral:       {cm_nb[1][0]:<8} | {cm_nb[1][1]:<12} | {cm_nb[1][2]:<13}")
    print(f"Actual Positive:      {cm_nb[2][0]:<8} | {cm_nb[2][1]:<12} | {cm_nb[2][2]:<13}")
    print("=" * 75 + "\n")

    return metadata


if __name__ == "__main__":
    run_training_and_evaluation()
