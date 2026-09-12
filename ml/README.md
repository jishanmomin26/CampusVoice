# CampusVoice — Machine Learning & NLP Pipeline

This directory contains the machine learning, feature engineering, and dataset transformation pipelines for **CampusVoice: AI-Powered Student Feedback Intelligence System**.

---

## 1. Dataset Overview

* **Source File**: `ml/datasets/finalDataset0.2.xlsx`
* **Source Description**: Provided institutional student-feedback survey dataset.
* **Dimensions**: 186 rows (1 header row + 185 student survey responses) × 12 columns.
* **Format**: Wide format with 6 paired category blocks (sentiment column + feedback-text column).

### Category Column Pair Mapping

| Fixed Indices | Sentiment Column in Excel | Text Column in Excel | Standardized Category Name |
| :---: | :--- | :--- | :--- |
| `(0, 1)` | `teaching` | `teaching` | **Teaching** |
| `(2, 3)` | `coursecontent` | `coursecontent` | **Course Content** |
| `(4, 5)` | `examination` | `Examination` | **Examination** |
| `(6, 7)` | `labwork` | `labwork` | **Lab Work** |
| `(8, 9)` | `library_facilities` | ` library_facilities` | **Library Facilities** |
| `(10, 11)`| `extracurricular` | `extracurricular` | **Extracurricular** |

---

## 2. Preprocessing & Transformation Pipeline

### Wide → Long Transformation
The wide survey format is unpivoted so that every student comment becomes an independent feedback record:
* Approximately $185 \times 6 = 1110$ potential records.

### Data Cleaning & Validation Rules
1. **Empty Text Filter**: Discards records where feedback text is missing, NaN, or whitespace-only.
2. **Sentiment Validation**: Validates that numeric sentiment belongs strictly to `{-1, 0, 1}`:
   * `-1` → `negative`
   * `0` → `neutral`
   * `1` → `positive`
3. **Category-Aware Deduplication**: Identical feedback across *different* categories (e.g., "Good" in Teaching and "Good" in Examination) is legitimately preserved. Identical feedback within the *same* category is deduplicated.
4. **ID Assignment**: Assigns a unique sequential integer `id` to each validated record.

### Step 3 NLP Preprocessing Integration
Each feedback record is passed through `backend/app/nlp/preprocessing.py:preprocess_text`:
* Normalization, lowercasing, and whitespace collapsing.
* Linguistic tokenization & lemmatization via spaCy (`en_core_web_sm`).
* Stopword removal with **sentiment negation preservation** (`not`, `no`, `never`, `n't`, `without`).
* Resulting cleaned text is stored in `clean_text`.

---

## 3. Train / Test Split

* **Ratio**: 80% Training (`train_feedback.csv`), 20% Testing (`test_feedback.csv`).
* **Random Seed**: `random_state=42` for guaranteed reproducibility.
* **Stratification**: Stratified on `sentiment` to preserve class proportions across splits.

---

## 4. TF-IDF Feature Engineering

* **Vectorizer**: `sklearn.feature_extraction.text.TfidfVectorizer`
* **Configuration**:
  * `ngram_range=(1, 2)`: Captures single words and meaningful bigrams (e.g. `"not helpful"`, `"lab computer"`).
  * `min_df=1`: Preserves low-frequency feedback terms suitable for small institutional datasets.
  * `max_df=0.95`: Filters ubiquitous corpus terms.
  * `sublinear_tf=True`: Sublinear scaling $1 + \log(\text{tf})$ to dampen high-frequency repetition.

### Strict Data Leakage Prevention
```text
Training Texts  ──> vectorizer.fit_transform()  ──> X_train matrix
                               │
                       Fitted Vocabulary
                               │
Testing Texts   ──> vectorizer.transform()      ──> X_test matrix
```
The vectorizer is **never** fit on the complete dataset. The test set is strictly evaluated against the training vocabulary.

---

## 5. Directory Structure & Generated Artifacts

```text
ml/
├── datasets/
│   ├── finalDataset0.2.xlsx      # Original raw dataset (UNTOUCHED)
│   ├── processed_feedback.csv    # Standardized long-format dataset
│   ├── train_feedback.csv        # 80% stratified training split (578 samples)
│   ├── test_feedback.csv         # 20% stratified testing split (145 samples)
│   └── dataset_summary.json      # Complete dataset audit and metrics
├── evaluation/
│   ├── evaluate_models.py        # Evaluation metrics & best model selection
│   ├── model_comparison.json     # Quantitative test evaluation metrics
│   └── confusion_matrix.json     # 3x3 confusion matrices & breakdowns
├── models/
│   ├── tfidf_vectorizer.joblib   # Fitted TF-IDF vectorizer (Step 4)
│   ├── logistic_regression_sentiment.joblib # Trained Logistic Regression
│   ├── naive_bayes_sentiment.joblib         # Trained MultinomialNB
│   ├── best_sentiment_model.joblib          # Selected best model (Macro F1)
│   ├── model_metadata.json       # Training metadata & per-class metrics
│   └── inference.py              # Real-time sentiment prediction utility
├── preprocessing/
│   ├── inspect_dataset.py        # Workbook inspection utility
│   ├── dataset_preparation.py    # Wide-to-long transformation & NLP pipeline
│   └── tfidf_features.py         # TF-IDF feature engineering module
├── tests/
│   ├── test_dataset_preparation.py # Automated test suite for Step 4
│   └── test_model_training.py      # Automated test suite for Step 5
├── training/
│   ├── train_models.py           # Model training functions
│   └── train_and_evaluate.py     # Master execution script for Step 5
├── run_pipeline.py               # Master execution script for Step 4
└── README.md
```

---

## 6. Step 5 — Baseline Sentiment Classification Models

### Candidate Models & Configurations

1. **Logistic Regression**
   * Class: `sklearn.linear_model.LogisticRegression`
   * Configuration: `max_iter=2000`, `random_state=42`, `class_weight='balanced'`
   * Rationale: Handles class imbalance across positive (majority), negative, and neutral classes with L2 regularization.

2. **Multinomial Naive Bayes**
   * Class: `sklearn.naive_bayes.MultinomialNB`
   * Configuration: `alpha=1.0` (Laplace smoothing)
   * Rationale: Classical probabilistic text baseline using discrete TF-IDF term counts.

### Evaluation & Model Selection Results (Held-Out Test Set)

Evaluated strictly on the held-out test set ($N = 145$ samples) using the Step 4 fitted TF-IDF vectorizer (2,720 features). **Selection Metric: Macro F1**.

| Metric | Logistic Regression (Balanced) | Multinomial Naive Bayes |
| :--- | :---: | :---: |
| **Accuracy** | **0.7241 (72.41%)** | 0.6552 (65.52%) |
| **Precision (Macro)** | 0.6201 | **0.8158** |
| **Recall (Macro)** | **0.6238** | 0.3933 |
| **F1-Score (Macro)** | **0.6217** *(Selected Best)* | 0.3666 |
| **Precision (Weighted)** | 0.7305 | 0.7426 |
| **Recall (Weighted)** | **0.7241** | 0.6552 |
| **F1-Score (Weighted)** | **0.7271** | 0.5480 |

### Per-Class Performance (Logistic Regression — Best Model)

| Class | Label | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Negative** | `-1` | 0.5714 | 0.5714 | 0.5714 | 28 |
| **Neutral** | `0` | 0.4138 | 0.4444 | 0.4286 | 27 |
| **Positive** | `1` | 0.8750 | 0.8556 | 0.8652 | 90 |
| **Macro Average** | — | **0.6201** | **0.6238** | **0.6217** | 145 |
| **Weighted Average** | — | **0.7305** | **0.7241** | **0.7271** | 145 |

### Confusion Matrices

#### Logistic Regression
```text
                 Pred Negative | Pred Neutral | Pred Positive
Actual Negative:      16       | 10           | 2
Actual Neutral:       6        | 12           | 9
Actual Positive:      6        | 7            | 77
```

#### Multinomial Naive Bayes
```text
                 Pred Negative | Pred Neutral | Pred Positive
Actual Negative:      4        | 0            | 24
Actual Neutral:       1        | 1            | 25
Actual Positive:      0        | 0            | 90
```

*Observation*: MultinomialNB suffered from severe majority-class collapse towards the positive class (90/90 positive recall, but almost completely failing to detect negative and neutral comments). Logistic Regression with balanced class weights significantly outperformed it by correctly identifying 16/28 negative and 12/27 neutral feedbacks.

---

## 7. Sentiment Inference Utility

Use `ml.models.inference.predict_sentiment`:

```python
from ml.models.inference import predict_sentiment

# Predict using best model (default)
result = predict_sentiment("The faculty is not helpful and rude.")
print(result)
# Output:
# {
#   'text': 'The faculty is not helpful and rude.',
#   'clean_text': 'faculty not helpful rude',
#   'sentiment': -1,
#   'sentiment_label': 'negative',
#   'model_used': 'best',
#   'probabilities': {'negative': 0.658, 'neutral': 0.231, 'positive': 0.111},
#   'confidence': 0.658
# }

# Explicit model selection: 'logistic_regression' or 'naive_bayes'
result = predict_sentiment("Great library collection!", model_name="naive_bayes")
```

---

## 8. How to Run

### 1. Run Step 5 Model Training & Evaluation
```powershell
python ml/training/train_and_evaluate.py
```

### 2. Run All Automated Tests
```powershell
pytest ml/tests/ -v
pytest backend/tests/ -v
```
