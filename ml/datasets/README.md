# CampusVoice — Datasets

Raw, processed, and partitioned datasets for the **CampusVoice** student feedback intelligence pipeline.

---

## 1. Raw Dataset Source

* **File**: `finalDataset0.2.xlsx`
* **Format**: Microsoft Excel OpenXML Spreadsheet (`.xlsx`)
* **Dimensions**: 186 rows (1 header row + 185 student survey responses) × 12 columns
* **Structure**: Wide-format survey where each student answered questions across six institutional categories. Each category consists of two paired columns: a numeric sentiment column followed by a free-form feedback text column.

### Category Column Pair Mapping in Raw Excel:
| Category Indices | Sentiment Column | Text Column | Target Category |
| :---: | :--- | :--- | :--- |
| `(0, 1)` | `teaching` | `teaching` | **Teaching** |
| `(2, 3)` | `coursecontent` | `coursecontent` | **Course Content** |
| `(4, 5)` | `examination` | `Examination` | **Examination** |
| `(6, 7)` | `labwork` | `labwork` | **Lab Work** |
| `(8, 9)` | `library_facilities` | ` library_facilities` | **Library Facilities** |
| `(10, 11)` | `extracurricular` | `extracurricular` | **Extracurricular** |

---

## 2. Wide-to-Long Transformation Pipeline

Executed by [`ml/preprocessing/dataset_preparation.py`](file:///d:/Projects%20Of%20JISHAN/CampusVoice/ml/preprocessing/dataset_preparation.py):

1. **Unpivoting**: The 185 multi-category wide survey rows are unpivoted into independent single-feedback records.
2. **Missing Text Filtering**: Records with missing, NaN, or whitespace-only feedback text are dropped.
3. **Sentiment Validation**: Verifies sentiment values belong strictly to `{-1, 0, 1}`:
   * `-1` $\rightarrow$ Negative
   * `0` $\rightarrow$ Neutral
   * `1` $\rightarrow$ Positive
4. **Category-Aware Deduplication**: Feedback comments identical across *different* categories (e.g., `"Good"` under Teaching vs. `"Good"` under Lab Work) are preserved. Identical comments within the *same* category are deduplicated.
5. **NLP Integration**: Runs raw text through `backend/app/nlp/preprocessing.py:preprocess_text` to generate `clean_text` (normalized, lemmatized, with sentiment negation preservation).

---

## 3. Dataset Files & Partitions

| File | Description | Sample Count |
| :--- | :--- | :---: |
| `finalDataset0.2.xlsx` | Original wide-format survey dataset (untouched source). | 185 rows |
| `processed_feedback.csv` | Standardized, cleaned, and lemmatized long-format dataset. | 723 records |
| `train_feedback.csv` | 80% stratified training partition (`random_state=42`). | 578 records |
| `test_feedback.csv` | 20% stratified held-out test partition (`random_state=42`). | 145 records |
| `dataset_summary.json` | Complete statistical metadata, vocabulary, and class distributions. | — |

---

## 4. Class & Category Distribution

### Category Breakdown (Total: 723 samples)
* **Teaching**: 125 samples (~17.3%)
* **Examination**: 129 samples (~17.8%)
* **Extracurricular**: 123 samples (~17.0%)
* **Course Content**: 120 samples (~16.6%)
* **Library Facilities**: 116 samples (~16.0%)
* **Lab Work**: 110 samples (~15.2%)

### Sentiment Breakdown (Total: 723 samples)
* **Positive (`1`)**: 448 samples (~62.0%)
* **Negative (`-1`)**: 140 samples (~19.4%)
* **Neutral (`0`)**: 135 samples (~18.7%)
