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

```

---

## 8. Step 6 — Feedback Category Classification Models

### Objective & Feedback Categories
CampusVoice automatically categorizes incoming student feedback comments into one of six institutional categories:
1. **Teaching**
2. **Course Content**
3. **Examination**
4. **Lab Work**
5. **Library Facilities**
6. **Extracurricular**

### Feature Representation & Train/Test Separation
- **Feature Matrix**: Reuses the pre-fitted Step 4 `TfidfVectorizer` (2,720 features) without refitting.
- **Data Partitions**: Strictly reuses the existing 80/20 stratified splits:
  - **Training Set**: 578 samples
  - **Held-Out Test Set**: 145 samples

### Candidate Classification Models
1. **Logistic Regression**
   * Class: `sklearn.linear_model.LogisticRegression`
   * Hyperparameters: `max_iter=2000`, `random_state=42`, `class_weight=None` (unweighted because category distributions are balanced).
2. **Multinomial Naive Bayes**
   * Class: `sklearn.naive_bayes.MultinomialNB`
   * Hyperparameters: `alpha=1.0` (Laplace smoothing).

### Evaluation & Model Selection Results (Held-Out Test Set)

Evaluated strictly on the held-out test partition ($N = 145$). **Model Selection Metric: Macro F1**.

| Metric | Logistic Regression | Multinomial Naive Bayes | Best Performer |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **0.6621 (66.21%)** | 0.6345 (63.45%) | **Logistic Regression** |
| **Precision (Macro)** | **0.6801** | 0.6715 | **Logistic Regression** |
| **Recall (Macro)** | **0.6620** | 0.6343 | **Logistic Regression** |
| **F1-Score (Macro)** | **0.6628** *(Selected Best)* | 0.6364 | **Logistic Regression (+4.1%)** |
| **Precision (Weighted)** | **0.6776** | 0.6664 | **Logistic Regression** |
| **Recall (Weighted)** | **0.6621** | 0.6345 | **Logistic Regression** |
| **F1-Score (Weighted)** | **0.6615** | 0.6339 | **Logistic Regression** |

### Per-Category Performance Breakdown (Best Model: Logistic Regression)

| Category | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Teaching** | 0.5926 | 0.6400 | 0.6154 | 25 |
| **Course Content** | 0.7308 | 0.7917 | 0.7600 | 24 |
| **Examination** | 0.7143 | 0.5769 | 0.6383 | 26 |
| **Lab Work** | 0.7500 | 0.6818 | 0.7143 | 22 |
| **Library Facilities** | 0.7500 | 0.5217 | 0.6154 | 23 |
| **Extracurricular** | 0.5429 | 0.7600 | 0.6333 | 25 |
| **Macro Average** | **0.6801** | **0.6620** | **0.6628** | **145** |
| **Weighted Average** | **0.6776** | **0.6621** | **0.6615** | **145** |

### 6×6 Confusion Matrices

#### Logistic Regression
```text
Actual / Pred       | Teaching | Course Con | Examinat | Lab Work | Library Fa | Extracurr
-----------------------------------------------------------------------------------------
Teaching            |    16    |     0      |    1     |    3     |     2      |    3
Course Content      |     1    |    19      |    1     |    1     |     0      |    2
Examination         |     3    |     1      |   15     |    1     |     1      |    5
Lab Work            |     1    |     2      |    3     |   15     |     0      |    1
Library Facilities  |     2    |     3      |    1     |    0     |    12      |    5
Extracurricular     |     4    |     1      |    0     |    0     |     1      |   19
```

#### Multinomial Naive Bayes
```text
Actual / Pred       | Teaching | Course Con | Examinat | Lab Work | Library Fa | Extracurr
-----------------------------------------------------------------------------------------
Teaching            |    16    |     1      |    2     |    3     |     1      |    2
Course Content      |     1    |    20      |    3     |    0     |     0      |    0
Examination         |     5    |     1      |   18     |    1     |     1      |    0
Lab Work            |     2    |     1      |    4     |   15     |     0      |    0
Library Facilities  |     3    |     3      |    4     |    0     |    11      |    2
Extracurricular     |     6    |     3      |    3     |    0     |     1      |   12
```

Visual plots generated via pure Matplotlib are saved in `ml/evaluation/results/`:
- `category_logistic_regression_confusion_matrix.png`
- `category_naive_bayes_confusion_matrix.png`

---

## 9. Reusable Category Inference Utility

Use `ml.models.category_inference.predict_category`:

```python
from ml.models.category_inference import predict_category

# Predict using best category model (default)
result = predict_category("The syllabus should include more modern cloud computing technologies.")
print(result)
# Output:
# {
#   'text': 'The syllabus should include more modern cloud computing technologies.',
#   'clean_text': 'syllabus include modern cloud compute technology',
#   'category': 'Course Content',
#   'confidence': 0.78,
#   'model_used': 'best',
#   'probabilities': {
#       'Course Content': 0.78,
#       'Teaching': 0.08,
#       'Lab Work': 0.06,
#       'Examination': 0.04,
#       'Extracurricular': 0.02,
#       'Library Facilities': 0.02
#   }
# }

# Explicit model selection: 'logistic_regression' or 'naive_bayes'
result = predict_category("The library needs more reference books.", model_name="naive_bayes")
```

---

## 10. Execution Commands

### 1. Run Category Model Training & Evaluation (Step 6)
```powershell
python ml/training/train_and_evaluate_category.py
```

### 2. Run Sentiment Model Training & Evaluation (Step 5)
```powershell
python ml/training/train_and_evaluate.py
```

### 3. Run Complete ML Test Suite
```powershell
pytest ml/tests/ -v
```

### 4. Run Backend Regression Tests
```powershell
pytest backend/tests/ -v
```

