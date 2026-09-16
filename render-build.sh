#!/usr/bin/env bash
# ==============================================================================
# CampusVoice — Render Build Script
# ==============================================================================
# Deterministic build script for Render deployment.
# Installs backend dependencies and downloads required NLTK resources (stopwords)
# at build time so the runtime container is immediately ready without startup downloads.
# ==============================================================================

set -e

echo "=== [1/2] Installing Python Dependencies ==="
pip install -r backend/requirements.txt

echo "=== [2/2] Installing Build-Time NLTK Resources ==="
python backend/scripts/install_nltk_resources.py

echo "=== Build Complete ==="
