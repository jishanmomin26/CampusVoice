# CampusVoice — Model Evaluation & Metrics

Evaluation scripts, quantitative metric reports, and confusion matrices for the **CampusVoice** machine learning pipelines.

---

## 1. Overview

This directory contains the model evaluation logic and output metrics. All evaluation is performed strictly on the held-out test partition ($N = 145$ samples) generated in Step 4, ensuring unbiased benchmarks.

---

## 2. Evaluation Scripts

### `evaluate_models.py` (Sentiment Classification)
Calculates quantitative metrics for candidate sentiment models:
* Overall accuracy.
* Macro and Weighted Precision, Recall, and F1-Score.
* Per-class metrics for Negative (`-1`), Neutral (`0`), and Positive (`1`).
* 3×3 confusion matrices mapping ground-truth vs. predicted labels.

### `evaluate_category_models.py` (Category Classification)
Calculates quantitative metrics for candidate category models:
* Overall accuracy across the 6 academic categories.
* Macro and Weighted Precision, Recall, and F1-Score.
* Per-category breakdown for *Teaching*, *Course Content*, *Examination*, *Lab Work*, *Library Facilities*, and *Extracurricular*.
* 6×6 confusion matrices and Matplotlib visualization plots.

---

## 3. Generated Evaluation Artifacts

| File | Description |
| :--- | :--- |
| `model_comparison.json` | Quantitative test comparison between Logistic Regression and Multinomial Naive Bayes for sentiment. |
| `confusion_matrix.json` | Detailed 3×3 confusion matrices and per-class reports for sentiment models. |
| `category_model_comparison.json` | Quantitative test comparison between Logistic Regression and Multinomial Naive Bayes across categories. |
| `category_results.txt` | Formatted text classification report covering all categories. |
| `results/category_logistic_regression_confusion_matrix.png` | Visual confusion matrix heatmap for Logistic Regression. |
| `results/category_naive_bayes_confusion_matrix.png` | Visual confusion matrix heatmap for Multinomial Naive Bayes. |

---

## 4. Key Performance Results (Test Set: $N = 145$)

### Sentiment Models
* **Logistic Regression (Balanced)**: Accuracy **72.41%**, Macro Precision **0.6201**, Macro Recall **0.6238**, Macro F1 **0.6217** *(Selected Best)*
* **Multinomial Naive Bayes**: Accuracy 65.52%, Macro Precision 0.8158, Macro Recall 0.3933, Macro F1 0.3666

### Category Models
* **Logistic Regression**: Accuracy **66.21%**, Macro Precision **0.6801**, Macro Recall **0.6620**, Macro F1 **0.6628** *(Selected Best)*
* **Multinomial Naive Bayes**: Accuracy 63.45%, Macro Precision 0.6715, Macro Recall 0.6343, Macro F1 0.6364
