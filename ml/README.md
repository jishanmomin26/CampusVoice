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
│   ├── train_feedback.csv        # 80% stratified training split
│   ├── test_feedback.csv         # 20% stratified testing split
│   └── dataset_summary.json      # Complete dataset audit and metrics
├── models/
│   └── tfidf_vectorizer.joblib   # Fitted scikit-learn TF-IDF vectorizer artifact
├── preprocessing/
│   ├── inspect_dataset.py        # Workbook inspection utility
│   ├── dataset_preparation.py    # Wide-to-long transformation & NLP pipeline
│   └── tfidf_features.py         # TF-IDF feature engineering module
├── tests/
│   └── test_dataset_preparation.py # Automated pytest suite
├── run_pipeline.py               # Master execution script for Step 4
└── README.md
```

---

## 6. How to Run

### 1. Run Dataset Inspection
```powershell
# From project root with venv activated:
python ml/preprocessing/inspect_dataset.py
```

### 2. Execute Full Step 4 Pipeline
```powershell
python ml/run_pipeline.py
```

### 3. Run Automated Tests
```powershell
pytest ml/tests/ -v
```
