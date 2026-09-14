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

---

## 11. Step 7 — Unified Feedback Intelligence Pipeline

### Overview
In Step 7, the separate machine learning and NLP components developed across Steps 3–6 are unified into a single, cohesive, and reusable inference pipeline. Rather than invoking preprocessing, feature transformation, sentiment analysis, and category prediction as fragmented scripts, the `FeedbackIntelligencePipeline` offers a clean, reusable inference engine that takes raw feedback text and produces complete sentiment and topic intelligence in a single call.

### Architecture & Conceptual Flow

```text
               Raw Student Feedback
                        ↓
          Step 3 NLP Preprocessing
          (Normalization + Lemmatization + Negation Preservation)
                        ↓
             Cleaned Normalized Text
                        ↓
          Step 4 Fitted TF-IDF Vectorizer
          (2,720 Features — transform() only, no refitting)
                        ↓
             Unified Feature Vector (X_vec)
                        │
         ┌──────────────┴──────────────┐
         ↓                             ↓
Step 5 Sentiment Model        Step 6 Category Model
(Logistic Regression / NB)    (Logistic Regression / NB)
         ↓                             ↓
Label, Name, Probs, Conf      Category, Probs, Conf
         └──────────────┬──────────────┘
                        ↓
        Unified Feedback Intelligence Output
```

### Key Design Principles
1. **Component Reuse**:
   - **Step 3 Preprocessing**: Reuses `backend/app/nlp/preprocessing.py:preprocess_text`. Preserves sentiment-critical negation tokens (`not`, `no`, `never`).
   - **Step 4 TF-IDF Features**: Loads `ml/models/tfidf_vectorizer.joblib` once. Strictly executes `transform()`; never calls `fit()` or `fit_transform()`.
   - **Step 5 Sentiment Models**: Reuses `ml/models/best_sentiment_model.joblib` (or model-specific variants).
   - **Step 6 Category Models**: Reuses `ml/models/best_category_model.joblib` (or model-specific variants).
2. **In-Memory Model Caching**:
   - Model artifacts and the vectorizer are loaded from disk once upon `FeedbackIntelligencePipeline` initialization.
   - Repeated calls to `pipeline.analyze_feedback(...)` reuse identical in-memory instances, eliminating redundant disk I/O and deserialization latency.
3. **Robust Input Validation**:
   - Validates that inputs are non-null strings with meaningful content.
   - Rejects `None`, empty strings `""`, whitespace-only strings, and non-string types with explicit exceptions (`ValueError`, `TypeError`).
4. **Stable Output Schema**:
   - Returns a structured dictionary containing input text, clean text, sentiment sub-object, category sub-object, and models used.

### Output Schema

```json
{
  "feedback": "The professor is not helpful and the explanations are not clear at all.",
  "clean_text": "faculty not helpful explanation not clear",
  "sentiment": {
    "label": -1,
    "name": "negative",
    "confidence": 0.5216,
    "probabilities": {
      "negative": 0.5216,
      "neutral": 0.3634,
      "positive": 0.1150
    }
  },
  "category": {
    "name": "Teaching",
    "confidence": 0.2507,
    "probabilities": {
      "Teaching": 0.2507,
      "Course Content": 0.2476,
      "Library Facilities": 0.1437,
      "Examination": 0.1348,
      "Lab Work": 0.1152,
      "Extracurricular": 0.1080
    }
  },
  "models": {
    "sentiment": "logistic_regression",
    "category": "logistic_regression"
  }
}
```

### Usage: Reusable Inference Pipeline

```python
from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline, analyze_feedback

# Option 1: Object-oriented pipeline with in-memory caching (Recommended for repeated calls)
pipeline = FeedbackIntelligencePipeline(sentiment_model="best", category_model="best")
result = pipeline.analyze_feedback("The laboratory equipment is outdated and not working.")
print(f"Sentiment: {result['sentiment']['name']} ({result['sentiment']['confidence']:.1%})")
print(f"Category:  {result['category']['name']} ({result['category']['confidence']:.1%})")

# Option 2: Convenience function with module-level singleton cache
quick_result = analyze_feedback("The library collection is fantastic and has quiet study spaces.")
print(quick_result["category"]["name"])  # 'Library Facilities'
```

### Execution Commands

```powershell
# 1. Run Step 7 Pipeline Demo
python ml/pipeline/run_demo.py

# 2. Run Step 7 Automated Test Suite (25 conditions)
pytest ml/tests/test_feedback_intelligence.py -v

# 3. Run Step 8.1 Priority Scoring Test Suite (21 conditions)
pytest ml/tests/test_priority_scoring.py -v

# 4. Run Complete ML Test Suite (80 tests)
pytest ml/tests/ -v

# 5. Run Backend Regression Tests (15 tests)
pytest backend/tests/ -v
```

---

## 12. Step 8.1 — Priority Scoring Engine

### Purpose
Educational institutions receive hundreds of student feedback comments across diverse departments. Institutional administrators need a transparent, explainable, and deterministic mechanism to prioritize incoming feedback for review without subjective guesswork or opaque scoring. 

The **Priority Scoring Engine** is a rule-based, deterministic scoring layer that converts Step 7 intelligence signals into an actionable priority score (0–100), an administrative priority level (`High`, `Medium`, `Low`), and a transparent reason.

> [!NOTE]
> This engine is strictly rule-based and explainable. It does **not** train or modify any machine learning models, does not refit TF-IDF, and does not use arbitrary keyword severity heuristics.

### Conceptual Flow

```text
               Step 7 Intelligence
                        ↓
             Sentiment + Confidence
                        +
             Category + Confidence
                        ↓
             Priority Scoring Engine
                        ↓
              Score + Level + Reason
```

### Deterministic Scoring Formula

1. **Primary Signal: Sentiment Base Score**
   - **Negative**:
     - Confidence $\ge 0.70 \implies \text{Base Score} = 80$
     - Confidence $\ge 0.50 \implies \text{Base Score} = 65$
     - Confidence $< 0.50 \implies \text{Base Score} = 50$
   - **Neutral**:
     - Confidence $\ge 0.70 \implies \text{Base Score} = 30$
     - Confidence $\ge 0.50 \implies \text{Base Score} = 25$
     - Confidence $< 0.50 \implies \text{Base Score} = 20$
   - **Positive**:
     - Confidence $\ge 0.70 \implies \text{Base Score} = 10$
     - Confidence $\ge 0.50 \implies \text{Base Score} = 5$
     - Confidence $< 0.50 \implies \text{Base Score} = 0$

2. **Secondary Signal: Category Confidence Adjustment**
   - Confidence $\ge 0.70 \implies +10$
   - Confidence $\ge 0.50 \implies +5$
   - Confidence $< 0.50 \implies +0$

3. **Score Clamping**:
   $$\text{Final Score} = \max(0, \min(100, \text{Base Score} + \text{Category Adjustment}))$$

### Priority Level Thresholds

| Final Score Range | Priority Level | Administrative Meaning |
| :---: | :---: | :--- |
| **70 – 100** | **High** | High-priority feedback requiring prompt administrative attention |
| **40 – 69** | **Medium** | Moderate-priority feedback for standard departmental review |
| **0 – 39** | **Low** | Routine inquiry or positive remarks with low immediate action priority |

### Reusable Usage Example

```python
from ml.priority.priority_scoring import PriorityScorer

scorer = PriorityScorer()

# Example 1: High-confidence negative feedback with clear category
result = scorer.calculate(
    sentiment_name="Negative",
    sentiment_confidence=0.82,
    category_name="Teaching",
    category_confidence=0.76,
)
print(result)
# Output:
# {
#     "score": 90,
#     "level": "High",
#     "reason": "Negative sentiment with high confidence and clearly identified feedback category."
# }

# Example 2: Directly from Step 7 intelligence output
from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline

pipeline = FeedbackIntelligencePipeline()
intelligence = pipeline.analyze_feedback("The laboratory computers are outdated.")
priority_result = scorer.calculate_from_intelligence(intelligence)
print(priority_result)
```

---

## 13. Step 8.2 — Priority Scoring Pipeline Integration

### Overview
Step 8.2 composes the existing Step 7 `FeedbackIntelligencePipeline` with the Step 8.1 `PriorityScorer`. When analyzing student feedback, the unified pipeline automatically performs priority calculation as an integrated post-inference step.

### Conceptual & Architectural Flow

```text
               Raw Feedback
                    ↓
             NLP Preprocessing
          (Step 3 Lemmatization &
          Negation Preservation)
                    ↓
             TF-IDF Transform
          (Step 4 Fitted Vectorizer)
                    ↓
           Sentiment + Category
          (Step 5 & Step 6 Models)
                    ↓
             PriorityScorer
          (Step 8.1 Rule Engine)
                    ↓
        Unified Intelligence Result
```

### Key Architectural Characteristics
1. **Compositional Design**: Step 8.2 composes existing components rather than duplicating logic. The `PriorityScorer` remains a standalone, reusable module (`ml.priority.priority_scoring.PriorityScorer`) that is cleanly instantiated and invoked by `FeedbackIntelligencePipeline`.
2. **Deterministic & Rule-Based**: The priority score (0–100), level (`High`, `Medium`, `Low`), and reason are computed via transparent, explainable formulas driven by the model predictions and their confidence scores.
3. **No Retraining or TF-IDF Refitting**: Underlying ML models (Logistic Regression / Naive Bayes) and the Step 4 TF-IDF vectorizer artifact are completely unchanged.
4. **Full Backward Compatibility**: All original Step 7 output fields (`feedback`, `clean_text`, `sentiment`, `category`, `models`) remain present and structured identically. The newly calculated priority is appended under the `"priority"` key.

### Unified Output Schema

```json
{
  "feedback": "The faculty is not helpful and the explanations are not clear at all.",
  "clean_text": "faculty not helpful explanation not clear",
  "sentiment": {
    "label": -1,
    "name": "negative",
    "confidence": 0.5216,
    "probabilities": {
      "negative": 0.5216,
      "neutral": 0.3634,
      "positive": 0.1150
    }
  },
  "category": {
    "name": "Teaching",
    "confidence": 0.2507,
    "probabilities": {
      "Teaching": 0.2507,
      "Course Content": 0.2476,
      "Library Facilities": 0.1437,
      "Examination": 0.1348,
      "Lab Work": 0.1152,
      "Extracurricular": 0.1080
    }
  },
  "models": {
    "sentiment": "logistic_regression",
    "category": "logistic_regression"
  },
  "priority": {
    "score": 65,
    "level": "Medium",
    "reason": "Negative sentiment detected with moderate confidence."
  }
}
```

### Reusable Usage Example

```python
from ml.pipeline.feedback_intelligence import FeedbackIntelligencePipeline, analyze_feedback

# Option 1: Object-oriented pipeline with in-memory caching
pipeline = FeedbackIntelligencePipeline(sentiment_model="best", category_model="best")
result = pipeline.analyze_feedback("The laboratory computers are outdated and not functioning well.")

print(f"Sentiment: {result['sentiment']['name']} ({result['sentiment']['confidence']:.1%})")
print(f"Category:  {result['category']['name']} ({result['category']['confidence']:.1%})")
print(f"Priority:  {result['priority']['level']} (Score: {result['priority']['score']}/100)")
print(f"Reason:    {result['priority']['reason']}")

# Option 2: Module-level convenience function
quick_result = analyze_feedback("The library has an excellent book collection.")
print(quick_result["priority"]["level"])  # "Low"
```

### Verification Commands

```powershell
# 1. Run Pipeline Demo with Priority Display
python ml/pipeline/run_demo.py

# 2. Run Step 7 & 8.2 Unified Pipeline Test Suite (41 tests)
pytest ml/tests/test_feedback_intelligence.py -v

# 3. Run Step 8.1 Standalone Priority Scorer Test Suite (21 tests)
pytest ml/tests/test_priority_scoring.py -v

# 4. Run Complete ML Suite (96 tests)
pytest ml/tests/ -v

# 5. Run Backend Regression Tests (15 tests)
pytest backend/tests/ -v
```




