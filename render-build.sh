#!/usr/bin/env bash
# render-build.sh

set -o errexit

echo "=== Instalando Tesseract OCR e dependências ==="
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils

echo "=== Verificando instalação do Tesseract ==="
tesseract --version
tesseract --list-langs

echo "=== Instalando dependências Python ==="
pip install -r requirements.txt