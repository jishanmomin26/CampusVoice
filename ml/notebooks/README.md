# CampusVoice — Notebooks Directory

This directory is reserved for exploratory data analysis (EDA), prototype prototyping, and experimental research notebooks.

---

## Current Status

* **Status**: Currently empty / reserved for future research.
* **Production Implementation**: All production NLP preprocessing, dataset preparation, TF-IDF feature engineering, model training, evaluation, priority scoring, and unified inference pipelines are fully implemented and maintained as modular Python packages in:
  * `ml/preprocessing/`
  * `ml/training/`
  * `ml/evaluation/`
  * `ml/priority/`
  * `ml/pipeline/`

## Guidelines for New Notebooks
* Notebooks added here should focus on exploratory data visualizations, hyperparameter tuning experiments, or new feature investigations.
* Do not commit large cell outputs containing confidential student feedback text.
* Production code should be refactored into the structured Python packages rather than called from notebooks in production.
