# CampusVoice — Model Training Pipelines

Machine Learning training pipelines for sentiment analysis and feedback category classification in **CampusVoice**.

---

## 1. Overview

This directory contains the model training and model selection pipelines. Both pipelines use the pre-fitted TF-IDF feature matrix from Step 4, train candidate models, evaluate performance on the held-out test partition ($N = 145$), select the optimal model based on Macro F1-score, and serialize the production artifacts to `ml/models/`.

---

## 2. Training Modules

### `train_models.py` & `train_and_evaluate.py` (Sentiment Classification)
Trains and compares candidate classifiers on student sentiment:
* **Classes**: `-1` (Negative), `0` (Neutral), `1` (Positive)
* **Candidates**:
  1. `LogisticRegression(max_iter=2000, random_state=42, class_weight='balanced')`
  2. `MultinomialNB(alpha=1.0)`
* **Master Script**: `python ml/training/train_and_evaluate.py`
  * Fits both models on the 578 training samples.
  * Evaluates strictly on the 145 held-out test samples.
  * Selects **Logistic Regression** (Macro F1: **0.6217** vs. Naive Bayes: 0.3666).
  * Serializes:
    * `ml/models/logistic_regression_sentiment.joblib`
    * `ml/models/naive_bayes_sentiment.joblib`
    * `ml/models/best_sentiment_model.joblib`
    * `ml/models/model_metadata.json`

### `train_category_models.py` & `train_and_evaluate_category.py` (Category Classification)
Trains and compares candidate classifiers on academic category classification:
* **Classes**: *Teaching*, *Course Content*, *Examination*, *Lab Work*, *Library Facilities*, *Extracurricular*
* **Candidates**:
  1. `LogisticRegression(max_iter=2000, random_state=42, class_weight=None)`
  2. `MultinomialNB(alpha=1.0)`
* **Master Script**: `python ml/training/train_and_evaluate_category.py`
  * Fits both models on the 578 training samples across the 6 categories.
  * Evaluates strictly on the 145 held-out test samples.
  * Selects **Logistic Regression** (Macro F1: **0.6628** vs. Naive Bayes: 0.6364).
  * Serializes:
    * `ml/models/logistic_regression_category.joblib`
    * `ml/models/naive_bayes_category.joblib`
    * `ml/models/best_category_model.joblib`
    * `ml/models/category_model_metadata.json`

---

## 3. Training Execution Commands

```powershell
# Execute Sentiment Training & Evaluation Pipeline
python ml/training/train_and_evaluate.py

# Execute Category Training & Evaluation Pipeline
python ml/training/train_and_evaluate_category.py
```
