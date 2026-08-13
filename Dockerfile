
FROM python:3.11-slim

# Variables d'environnement Python
# PYTHONDONTWRITEBYTECODE : pas de fichiers .pyc dans le conteneur
# PYTHONUNBUFFERED : les print() s'affichent en temps réel dans les logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dépendances système
# pdfplumber s'appuie sur des libs système pour lire certains PDF.
# On installe le minimum, puis on nettoie le cache apt pour alléger l'image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail dans le conteneur
WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


COPY . .

EXPOSE 8000

CMD uvicorn dashboard_app:app --host 0.0.0.0 --port ${PORT:-8000}