"""Feedback Category Classification - Model Evaluation Module.

Evaluates category classification models on the held-out test set,
computes classification metrics, generates 6x6 confusion matrix plots
using pure matplotlib (no seaborn), and exports structured evaluation artifacts.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend suitable for headless scripts
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

# Add project base directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Canonical categories in fixed order
CANONICAL_CATEGORIES: List[str] = [
    "Teaching",
    "Course Content",
    "Examination",
    "Lab Work",
    "Library Facilities",
    "Extracurricular",
]


def evaluate_category_model(
    model,
    X_test,
    y_test,
    class_names: List[str] | None = None,
) -> Dict[str, Any]:
    """Evaluates a category classifier on held-out test data.

    Args:
        model: Trained scikit-learn model.
        X_test: Test feature matrix.
        y_test: Test target category labels.
        class_names: List of category names for ordering.

    Returns:
        Dictionary containing all evaluation metrics, per-category breakdown,
        and 6x6 confusion matrix.
    """
    if class_names is None:
        class_names = CANONICAL_CATEGORIES

    y_pred = model.predict(X_test)

    # Global accuracy
    acc = float(accuracy_score(y_test, y_pred))

    # Macro-averaged metrics
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )

    # Weighted-averaged metrics
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )

    # Detailed classification report
    report_dict = classification_report(
        y_test,
        y_pred,
        labels=class_names,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    per_category = {}
    for cat in class_names:
        if cat in report_dict:
            per_category[cat] = {
                "precision": float(report_dict[cat]["precision"]),
                "recall": float(report_dict[cat]["recall"]),
                "f1_score": float(report_dict[cat]["f1-score"]),
                "support": int(report_dict[cat]["support"]),
            }

    # 6x6 Confusion Matrix
    cm = confusion_matrix(y_test, y_pred, labels=class_names)
    cm_list = cm.tolist()

    cm_breakdown = {}
    for i, actual_cat in enumerate(class_names):
        cm_breakdown[actual_cat] = {
            f"pred_{pred_cat}": int(cm[i, j])
            for j, pred_cat in enumerate(class_names)
        }

    return {
        "accuracy": acc,
        "precision_macro": float(p_macro),
        "recall_macro": float(r_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(p_weighted),
        "recall_weighted": float(r_weighted),
        "f1_weighted": float(f1_weighted),
        "per_category": per_category,
        "support_total": int(len(y_test)),
        "confusion_matrix": {
            "categories": class_names,
            "matrix": cm_list,
            "breakdown": cm_breakdown,
        },
    }


def compare_and_select_best_category_model(
    evaluation_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Selects the best model using Macro F1-score as the sole criterion.

    Args:
        evaluation_results: Mapping of model_name -> evaluation metrics dict.

    Returns:
        Dictionary with selection decision, best model name, and comparison summary.
    """
    best_model_name = None
    best_macro_f1 = -1.0

    models_summary = {}
    for model_name, metrics in evaluation_results.items():
        macro_f1 = metrics["f1_macro"]
        models_summary[model_name] = {
            "accuracy": metrics["accuracy"],
            "precision_macro": metrics["precision_macro"],
            "recall_macro": metrics["recall_macro"],
            "f1_macro": metrics["f1_macro"],
            "precision_weighted": metrics["precision_weighted"],
            "recall_weighted": metrics["recall_weighted"],
            "f1_weighted": metrics["f1_weighted"],
        }
        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_model_name = model_name

    return {
        "selected_metric": "f1_macro",
        "best_model": best_model_name,
        "best_macro_f1": best_macro_f1,
        "models": models_summary,
    }


def plot_category_confusion_matrix(
    cm: np.ndarray,
    class_names: List[str],
    title: str,
    output_path: Path,
) -> None:
    """Generates and saves a 6x6 confusion matrix plot using pure matplotlib (no seaborn).

    Args:
        cm: 2D numpy array confusion matrix.
        class_names: Category labels.
        title: Plot title.
        output_path: Destination PNG image path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=300)
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)

    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Count", rotation=-90, va="bottom", fontsize=11, fontweight="bold")

    # Set tick marks and category labels
    num_classes = len(class_names)
    ax.set_xticks(np.arange(num_classes))
    ax.set_yticks(np.arange(num_classes))
    ax.set_xticklabels(class_names, rotation=30, ha="right", fontsize=10, fontweight="medium")
    ax.set_yticklabels(class_names, fontsize=10, fontweight="medium")

    # Set labels and title
    ax.set_ylabel("Actual Category", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_xlabel("Predicted Category", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

    # Annotate numbers in each cell
    thresh = cm.max() / 2.0 if cm.max() > 0 else 1.0
    for i in range(num_classes):
        for j in range(num_classes):
            val = int(cm[i, j])
            color = "white" if val > thresh else "black"
            ax.text(
                j, i, f"{val}",
                ha="center", va="center",
                color=color, fontsize=11, fontweight="bold",
            )

    fig.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def export_category_evaluation_artifacts(
    evaluation_results: Dict[str, Dict[str, Any]],
    comparison_summary: Dict[str, Any],
    eval_dir: Path | None = None,
) -> Tuple[Path, Path]:
    """Saves category_model_comparison.json and category_results.txt.

    Args:
        evaluation_results: Full results for all models.
        comparison_summary: Summary of model comparison and best selection.
        eval_dir: Directory for evaluation files.

    Returns:
        Tuple of (json_path, txt_path).
    """
    if eval_dir is None:
        eval_dir = BASE_DIR / "ml" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    # 1. category_model_comparison.json
    json_path = eval_dir / "category_model_comparison.json"
    full_json_payload = {
        "selection_decision": comparison_summary,
        "evaluation_results": evaluation_results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_json_payload, f, indent=2)

    # 2. category_results.txt (human-readable comparison report)
    txt_path = eval_dir / "category_results.txt"
    lines = [
        "=" * 80,
        "CAMPUSVOICE - STEP 6: CATEGORY CLASSIFICATION EVALUATION REPORT",
        "=" * 80,
        f"Evaluation Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Selection Metric: {comparison_summary['selected_metric'].upper()}",
        f"Best Model:       {comparison_summary['best_model'].upper()}",
        f"Best Macro F1:    {comparison_summary['best_macro_f1']:.4f}",
        "",
        "-" * 80,
        "MODEL PERFORMANCE COMPARISON (HELD-OUT TEST SET)",
        "-" * 80,
        f"{'Model':<25} | {'Accuracy':<10} | {'Macro F1':<10} | {'Weighted F1':<12} | {'Macro Recall':<12}",
        "-" * 80,
    ]

    for model_name, metrics in comparison_summary["models"].items():
        lines.append(
            f"{model_name:<25} | {metrics['accuracy']:<10.4f} | {metrics['f1_macro']:<10.4f} | "
            f"{metrics['f1_weighted']:<12.4f} | {metrics['recall_macro']:<12.4f}"
        )
    lines.append("-" * 80)
    lines.append("")

    # Detailed per-category breakdown for each model
    for model_name, metrics in evaluation_results.items():
        lines.append("=" * 80)
        lines.append(f"DETAILED PER-CATEGORY METRICS: {model_name.upper()}")
        lines.append("=" * 80)
        lines.append(f"{'Category':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
        lines.append("-" * 80)
        for cat, cat_m in metrics["per_category"].items():
            lines.append(
                f"{cat:<22} | {cat_m['precision']:<10.4f} | {cat_m['recall']:<10.4f} | "
                f"{cat_m['f1_score']:<10.4f} | {cat_m['support']:<8}"
            )
        lines.append("-" * 80)
        lines.append(
            f"{'Macro Average':<22} | {metrics['precision_macro']:<10.4f} | {metrics['recall_macro']:<10.4f} | "
            f"{metrics['f1_macro']:<10.4f} | {metrics['support_total']:<8}"
        )
        lines.append(
            f"{'Weighted Average':<22} | {metrics['precision_weighted']:<10.4f} | {metrics['recall_weighted']:<10.4f} | "
            f"{metrics['f1_weighted']:<10.4f} | {metrics['support_total']:<8}"
        )
        lines.append("")

        # 6x6 Confusion Matrix printout
        lines.append(f"6x6 CONFUSION MATRIX ({model_name.upper()}):")
        cm_cats = metrics["confusion_matrix"]["categories"]
        cm_matrix = metrics["confusion_matrix"]["matrix"]
        header_str = f"{'Actual / Pred':<22} | " + " | ".join(f"{c[:10]:<10}" for c in cm_cats)
        lines.append(header_str)
        lines.append("-" * len(header_str))
        for i, actual_cat in enumerate(cm_cats):
            row_str = f"{actual_cat:<22} | " + " | ".join(f"{cm_matrix[i][j]:<10}" for j in range(len(cm_cats)))
            lines.append(row_str)
        lines.append("-" * len(header_str))
        lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, txt_path
