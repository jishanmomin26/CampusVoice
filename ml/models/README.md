# CampusVoice — Serialized Models & Inference Modules

Serialized model artifacts, pre-fitted vectorizers, and real-time inference utilities for **CampusVoice**.

---

## 1. Production Model Artifacts

This directory stores the serialized machine learning artifacts used by the unified feedback intelligence pipeline:

| Artifact | Type | Description |
| :--- | :--- | :--- |
| `tfidf_vectorizer.joblib` | Scikit-learn `TfidfVectorizer` | Pre-fitted feature extractor (2,720 unigram/bigram features). Fitted strictly on training data. |
| `best_sentiment_model.joblib` | Scikit-learn `LogisticRegression` | Production sentiment classifier (Macro F1: 0.6217). Classifies text into Negative (`-1`), Neutral (`0`), or Positive (`1`). |
| `best_category_model.joblib` | Scikit-learn `LogisticRegression` | Production category classifier (Macro F1: 0.6628). Classifies text into one of 6 institutional categories. |
| `model_metadata.json` | JSON Metadata | Training configuration, hyperparameters, and per-class metrics for sentiment models. |
| `category_model_metadata.json` | JSON Metadata | Training configuration, hyperparameters, and per-class metrics for category models. |

---

## 2. Real-Time Inference Utilities

### `inference.py` (Sentiment Prediction)
Exposes `predict_sentiment(text: str, model_name: str = "best")`:
* Accepts raw feedback text.
* Transforms text using `tfidf_vectorizer.joblib`.
* Predicts numeric sentiment (`-1`, `0`, `1`), textual label (`negative`, `neutral`, `positive`), confidence score, and probability distribution.

### `category_inference.py` (Category Prediction)
Exposes `predict_category(text: str, model_name: str = "best")`:
* Accepts raw feedback text.
* Transforms text using `tfidf_vectorizer.joblib`.
* Predicts the target academic category (*Teaching*, *Course Content*, *Examination*, *Lab Work*, *Library Facilities*, *Extracurricular*), confidence score, and per-category probability distribution.

---

## 3. In-Memory Caching & Performance

In the production `FeedbackIntelligencePipeline` (`ml/pipeline/feedback_intelligence.py`), model binaries are deserialized from disk once upon initial instantiation and cached in memory as a singleton. Subsequent inference requests reuse the in-memory models, avoiding redundant disk I/O and achieving sub-10ms inference latencies.

---

## 4. Version Control Policy (`.gitignore`)

To keep repository size manageable while ensuring the application deploys reliably without requiring model retraining in CI/CD:
* **Tracked Production Artifacts** (explicitly allowed in `.gitignore`):
  * `!ml/models/tfidf_vectorizer.joblib`
  * `!ml/models/best_sentiment_model.joblib`
  * `!ml/models/best_category_model.joblib`
  * `model_metadata.json`
  * `category_model_metadata.json`
* **Ignored Local Checkpoints**:
  * `logistic_regression_sentiment.joblib`
  * `naive_bayes_sentiment.joblib`
  * `logistic_regression_category.joblib`
  * `naive_bayes_category.joblib`
