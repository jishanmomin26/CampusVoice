"""Model Evaluation & Comparison Module for CampusVoice.

Evaluates trained classification models on the held-out test dataset,
computes comprehensive performance metrics, produces confusion matrices,
and determines the superior model based on Macro F1 score.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

CLASS_NAMES = {-1: "negative", 0: "neutral", 1: "positive"}
CLASS_LABELS = [-1, 0, 1]


def evaluate_model(
    model: Any,
    X_test: Any,
    y_test: pd.Series | np.ndarray,
) -> Dict[str, Any]:
    """Computes comprehensive evaluation metrics on the held-out test set.

    Args:
        model: Fitted scikit-learn classifier.
        X_test: Test TF-IDF feature matrix.
        y_test: True test sentiment labels.

    Returns:
        Dict[str, Any]: Dictionary containing accuracy, macro/weighted metrics,
                        per-class metrics, support, and confusion matrix.
    """
    y_pred = model.predict(X_test)
    y_true = np.array(y_test)

    acc = float(accuracy_score(y_true, y_pred))

    # Macro metrics
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )

    # Weighted metrics
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    # Per-class metrics
    p_class, r_class, f1_class, support_class = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASS_LABELS, zero_division=0
    )

    per_class_metrics: Dict[str, Dict[str, float]] = {}
    for idx, label in enumerate(CLASS_LABELS):
        name = CLASS_NAMES[label]
        per_class_metrics[name] = {
            "label_int": label,
            "precision": float(p_class[idx]),
            "recall": float(r_class[idx]),
            "f1_score": float(f1_class[idx]),
            "support": int(support_class[idx]),
        }

    # Confusion matrix with labels [-1, 0, 1]
    cm = confusion_matrix(y_true, y_pred, labels=CLASS_LABELS)

    # Structured confusion matrix dict
    cm_dict = {
        "labels": CLASS_LABELS,
        "class_names": [CLASS_NAMES[l] for l in CLASS_LABELS],
        "matrix": cm.tolist(),
        "breakdown": {
            f"actual_{CLASS_NAMES[actual]}": {
                f"pred_{CLASS_NAMES[pred]}": int(cm[i, j])
                for j, pred in enumerate(CLASS_LABELS)
            }
            for i, actual in enumerate(CLASS_LABELS)
        },
    }

    return {
        "accuracy": acc,
        "precision_macro": float(p_macro),
        "recall_macro": float(r_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(p_weighted),
        "recall_weighted": float(r_weighted),
        "f1_weighted": float(f1_weighted),
        "per_class": per_class_metrics,
        "support_total": int(len(y_true)),
        "confusion_matrix": cm_dict,
    }


def compare_and_select_best_model(
    evaluation_results: Dict[str, Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """Compares candidate models on held-out test data and selects the best by Macro F1.

    Args:
        evaluation_results: Dict mapping model_name -> evaluation metrics dict.

    Returns:
        Tuple[str, Dict[str, Any]]: (best_model_name, comparison_summary).
    """
    best_model_name = ""
    best_macro_f1 = -1.0

    summary_table: Dict[str, Any] = {}

    for name, metrics in evaluation_results.items():
        macro_f1 = metrics["f1_macro"]
        summary_table[name] = {
            "accuracy": metrics["accuracy"],
            "f1_macro": metrics["f1_macro"],
            "f1_weighted": metrics["f1_weighted"],
            "precision_macro": metrics["precision_macro"],
            "recall_macro": metrics["recall_macro"],
        }
        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_model_name = name

    comparison = {
        "selected_metric": "f1_macro",
        "best_model": best_model_name,
        "best_macro_f1": best_macro_f1,
        "models": summary_table,
    }

    return best_model_name, comparison
