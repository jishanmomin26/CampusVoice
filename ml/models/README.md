# Serialized Models & Artifacts

This directory stores serialized model binaries, vectorizers, and tokenizer artifacts for inference.

## Artifact Types
* `*.joblib` / `*.pkl`: Scikit-learn models (TF-IDF vectorizers, classifiers).
* `*.keras` / `*.h5`: TensorFlow deep learning weights and network architectures.
* `*.model` / `*.kv`: Gensim Word2Vec / FastText embedding matrices.

> **Note**: Binary model files are excluded from Git via `.gitignore`. Store small demo checkpoints or download links here when ready for deployment.
