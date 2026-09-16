#!/usr/bin/env bash
set -e

pip install -r backend/requirements.txt

python backend/scripts/install_nltk_resources.py

python backend/scripts/install_spacy_model.py
