# CampusVoice — Preprocessing & Feature Engineering

Text preprocessing, dataset transformation, and TF-IDF feature extraction modules for the **CampusVoice** machine learning pipeline.

---

## 1. Overview

This directory houses the data preparation scripts that transform the raw Excel feedback survey into standardized, clean text records, as well as the feature engineering modules that generate the numerical representation used for model training and inference.

---

## 2. Preprocessing Modules

### `dataset_preparation.py`
The master dataset transformation script:
* Reads `ml/datasets/finalDataset0.2.xlsx`.
* Unpivots the wide multi-column format into independent feedback comments across the six target academic categories.
* Filters missing, NaN, or whitespace-only records and standardizes sentiment labels to `{-1, 0, 1}`.
* Eliminates within-category duplicate comments while preserving identical remarks across different categories.
* Integrates `backend/app/nlp/preprocessing.py:preprocess_text` to generate normalized, lemmatized `clean_text` with **sentiment negation preservation** (`not`, `no`, `never`, `n't`).
* Performs an 80/20 stratified train/test split (`random_state=42`), outputting:
  * `ml/datasets/processed_feedback.csv`
  * `ml/datasets/train_feedback.csv` (578 samples)
  * `ml/datasets/test_feedback.csv` (145 samples)
  * `ml/datasets/dataset_summary.json`

### `inspect_dataset.py`
A diagnostic utility for inspecting the raw Excel survey structure, verifying column headers, validating expected indices, and checking data types prior to running pipeline transformations.

### `tfidf_features.py`
Feature extraction and vectorization module:
* Uses `sklearn.feature_extraction.text.TfidfVectorizer`.
* **Configuration**:
  * `ngram_range=(1, 2)`: Captures unigrams and bigrams (e.g., `"helpful"`, `"not helpful"`).
  * `min_df=1`: Preserves domain-specific low-frequency vocabulary.
  * `max_df=0.95`: Eliminates corpus-wide ubiquitous words.
  * `sublinear_tf=True`: Uses $1 + \log(\text{tf})$ scaling to dampen term repetition effects.
* **Strict Anti-Leakage Protocol**:
  * `fit_transform()` is executed strictly on the training partition (`train_feedback.csv`), resulting in a 2,720-feature vocabulary.
  * The held-out test partition (`test_feedback.csv`) is transformed using `transform()` only.
  * Saves the fitted vectorizer artifact to `ml/models/tfidf_vectorizer.joblib`.

---

## 3. Resource Requirements

The preprocessing pipeline relies on two external NLP resources:
1. **spaCy `en_core_web_sm`**: English language model for tokenization, part-of-speech analysis, and lemmatization.
2. **NLTK `stopwords`**: English stopword corpus with sentiment negations preserved.

To install these resources:
```powershell
python backend/scripts/install_nltk_resources.py
python backend/scripts/install_spacy_model.py
```
