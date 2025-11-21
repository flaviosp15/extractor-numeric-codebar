FROM python:3.12-slim

# Instalar Tesseract e dependências
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primeiro (para cache de layers)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar o código
COPY . .

# Expor a porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "server.index:app", "--host", "0.0.0.0", "--port", "8000"]