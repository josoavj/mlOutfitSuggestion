FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système nécessaires pour ChromaDB et le ML
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source et des données initiales (corpus RAG, modèles)
COPY . .

# Création des dossiers de données (pour le futur montage de volume Render)
RUN mkdir -p data/wardrobe data/preferences data/corpus_style data/feedback data/quality

# Port par défaut pour Render
EXPOSE 8000

# Lancement de l'API (on désactive le reload en production)
CMD ["uvicorn", "src.outfit_ml.api:app", "--host", "0.0.0.0", "--port", "8000"]
