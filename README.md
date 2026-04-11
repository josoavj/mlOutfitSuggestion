# ML Outfit Suggestion

Base de projet ML pour proposer des tenues personnalisees pour MagicMirror selon:
- sexe
- age
- taille
- planning du jour
- preferences vestimentaires
- morphologie (detectee automatiquement si mesures disponibles)
- meteo et lieu

## Architecture

Le systeme est compose de 3 parties:

1. Detection de morphologie:
- Si l'utilisateur fournit ses mesures (epaules, taille, hanches), la morphologie est deduite automatiquement.

2. Scoring ML de tenue:
- Un modele de classification binaire evalue la compatibilite utilisateur/contexte/tenue.
- Les tenues sont triees par probabilite de pertinence.

3. API de recommandation:
- Endpoint FastAPI qui retourne un top-k de tenues.

## Prerequis

- Python 3.11+

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Entrainement du modele

```bash
python -m src.outfit_ml.train --samples 4000
```

Le modele est sauvegarde dans:
- models/outfit_ranker.joblib
- models/outfit_ranker_metrics.json

Validation du dataset structure (option recommandee avant entrainement):

```bash
python -m src.outfit_ml.validate_dataset --dataset-root data/dataset
```

Conversion du dataset CSV vers Parquet partitionne par date:

```bash
python -m src.outfit_ml.export_parquet --dataset-root data/dataset --output-root data/parquet
```

## Lancer l'API

Option rapide recommandee avec `.env`:

```bash
cp .env.example .env
# edite .env puis renseigne tes vraies valeurs
uvicorn src.outfit_ml.api:app --reload
```

L'API charge automatiquement les variables depuis `.env`.

Option via export shell:

```bash
export OPENWEATHER_API_KEY="ta_cle_openweather"
uvicorn src.outfit_ml.api:app --reload
```

## Liaison API avec l'application (MagicMirror/Flutter)

Le service expose une API FastAPI consommee directement par l'application.

Configuration minimale recommandee:

```env
API_AUTH_ENABLED=true
API_AUTH_KEY=replace_with_strong_shared_secret
ALLOWED_ORIGINS=https://your-magicmirror-app.example.com
```

L'application doit envoyer l'entete HTTP suivant:

```text
X-API-Key: replace_with_strong_shared_secret
```

Endpoint principal recommande cote app:
- `POST /mirror/recommend-from-camera`

Ce endpoint couvre le flux complet (identification + contexte + recommandations).

## Mode integration automatique (direct application)

Pour une integration directe, configure l'API de ton application:

```bash
export MAGICMIRROR_API_BASE_URL="https://ton-app.example.com"
export MAGICMIRROR_API_TOKEN="token_optionnel"
export MAGICMIRROR_PROFILE_PATH_TEMPLATE="/api/users/{user_id}/profile"
export MAGICMIRROR_AGENDA_PATH_TEMPLATE="/api/users/{user_id}/agenda/today"
```

Puis appelle:

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "location": "Lyon",
    "top_k": 3
  }'
```

Dans ce mode, le service fait automatiquement:
- lecture du profil utilisateur (sexe, age, taille, preferences, morphologie)
- lecture de l'agenda du jour depuis l'application
- recuperation de la meteo via OpenWeather
- recommandation top-k sans payload manuel complexe

## Si tu n'as pas encore d'API MagicMirror

Tu peux fonctionner en mode fichier local tout de suite:

1. Utiliser les fichiers JSON locaux:
- `data/users/u-001/profile.json`
- `data/users/u-001/agenda_today.json`

2. Configurer `.env`:

```bash
MAGICMIRROR_DATA_SOURCE=file
OPENWEATHER_API_KEY=ta_cle_openweather
MAGICMIRROR_PROFILE_FILE_TEMPLATE=data/users/{user_id}/profile.json
MAGICMIRROR_AGENDA_FILE_TEMPLATE=data/users/{user_id}/agenda_today.json
```

3. Appeler le endpoint auto:

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "top_k": 3
  }'
```

Ensuite, quand ton API backend sera disponible, il suffira de passer `MAGICMIRROR_DATA_SOURCE=api`.

## Identification faciale (camera) pour miroir intelligent

Le projet inclut un module local d'identification faciale:
- enrôlement d'un visage pour un utilisateur
- identification d'une personne depuis une image camera

Configuration:

```bash
pip install face-recognition
export FACE_REGISTRY_PATH=data/vision/face_registry.json
```

Endpoints:

1. Enrôler un utilisateur

`POST /vision/enroll`

Payload:

```json
{
  "user_id": "u-001",
  "image_base64": "data:image/jpeg;base64,..."
}
```

2. Identifier un visage

`POST /vision/identify`

Payload:

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "threshold": 0.45,
  "max_results": 1
}
```

Recommandations production:
- utiliser uniquement sur consentement explicite utilisateur
- conserver les donnees en local (pas d'envoi cloud)
- ajouter un anti-spoofing (liveness) avant de valider l'identite

### Endpoint unique Android/Web/Webcam

Pour un flux simple cote application (camera integree), utilise:

`POST /mirror/recommend-from-camera`

Payload:

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "location": "Lyon",
  "threshold": 0.45,
  "top_k": 3
}
```

Ce endpoint fait automatiquement:
1. identification faciale
2. recuperation du profil + agenda du jour
3. recuperation meteo OpenWeather
4. retour des suggestions de tenue

Donc cote Android/Web/Webcam: une seule requete a envoyer apres capture camera.

## Recommandation depuis contexte reel (agenda + meteo)

Utilise cet endpoint quand l'application a deja les donnees agenda integrees.
La meteo est recuperee automatiquement via OpenWeather a partir de `location`.

```bash
curl -X POST "http://127.0.0.1:8000/recommend/context" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "gender": "female",
    "age": 29,
    "height_cm": 168,
    "clothing_size": "m",
    "top_size": "m",
    "bottom_size": "m",
    "shoe_size": "40",
    "style_preferences": ["minimalist", "elegant"],
    "body_measurements": {
      "shoulders_cm": 95,
      "waist_cm": 70,
      "hips_cm": 98
    },
    "agenda_entries": [
      {"title": "Daily Work Meeting", "category": "work", "tags": ["office"]},
      {"title": "Client presentation", "category": "meeting", "tags": ["formal"]}
    ],
    "location": "Lyon",
    "top_k": 3
  }'
```

## Exemple d'appel

```bash
curl -X POST "http://127.0.0.1:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "gender": "female",
    "age": 29,
    "height_cm": 168,
    "clothing_size": "m",
    "top_size": "m",
    "bottom_size": "m",
    "shoe_size": "40",
    "style_preferences": ["minimalist", "elegant"],
    "body_measurements": {
      "shoulders_cm": 95,
      "waist_cm": 70,
      "hips_cm": 98
    },
    "agenda": ["work", "meeting"],
    "location": "Lyon",
    "weather": {
      "temperature_c": 14,
      "condition": "rain"
    },
    "top_k": 3
  }'
```

## Limites et suite

- Le jeu de donnees d'entrainement est synthetique (bootstrapping).
- Pour la production, remplacer par de vraies interactions utilisateurs et feedback implicite/explicite.
- Integrer une source meteo reelle et agenda reel pour MagicMirror.

## Collecte feedback (donnees reelles)

Endpoints:
- `POST /feedback/event`
- `POST /feedback/events`
- `GET /feedback/stats`

Exemple d'evenement:

```json
{
  "session_id": "s-001",
  "user_id": "u-001",
  "outfit_id": "smart_casual",
  "event_type": "impression",
  "position": 0,
  "gender": "female",
  "age": 29,
  "height_cm": 168,
  "clothing_size": "m",
  "top_size": "m",
  "bottom_size": "m",
  "shoe_size": "40",
  "body_shape": "hourglass",
  "style_preferences": ["minimalist", "elegant"],
  "dominant_occasion": "work",
  "weather_bucket": "rainy"
}
```

## Entrainement avec donnees reelles

Le trainer peut utiliser les feedbacks reels et fallback sur le synthetique.

```bash
python -m src.outfit_ml.train \
  --prefer-real-data \
  --real-feedback-log data/feedback/events.jsonl \
  --min-real-samples 200 \
  --split-mode time
```

Metriques ajoutees si `session_id` est present:
- `precision_at_3`
- `recall_at_3`
- `ndcg_at_3`

Exemple batch (session complete en un appel):

```json
{
  "events": [
    {
      "session_id": "s-001",
      "user_id": "u-001",
      "outfit_id": "smart_casual",
      "event_type": "impression",
      "position": 0,
      "gender": "female",
      "age": 29,
      "height_cm": 168,
      "clothing_size": "m",
      "top_size": "m",
      "bottom_size": "m",
      "shoe_size": "40",
      "body_shape": "hourglass",
      "style_preferences": ["minimalist", "elegant"],
      "dominant_occasion": "work",
      "weather_bucket": "rainy"
    },
    {
      "session_id": "s-001",
      "user_id": "u-001",
      "outfit_id": "smart_casual",
      "event_type": "selected",
      "position": 0,
      "gender": "female",
      "age": 29,
      "height_cm": 168,
      "body_shape": "hourglass",
      "style_preferences": ["minimalist", "elegant"],
      "dominant_occasion": "work",
      "weather_bucket": "rainy"
    }
  ]
}
```
