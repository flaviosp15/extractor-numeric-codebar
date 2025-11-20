#!/bin/bash

echo "🚀 Iniciando aplicação em modo produção..."

# Verificar se todas as dependências do sistema estão instaladas
command -v tesseract >/dev/null 2>&1 || { echo "❌ Tesseract não instalado"; exit 1; }
command -v pdftoppm >/dev/null 2>&1 || { echo "❌ Poppler utils não instalado"; exit 1; }

# Executar a aplicação
exec gunicorn server.index:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 \
    --keep-alive 5