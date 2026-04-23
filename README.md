# ML Outfit Suggestion

> Base de projet ML pour proposer des tenues personnalisées pour [MagicMirror](https://github.com/josoavj/magicmirror) selon le profil utilisateur et le contexte du jour.

**Critères pris en compte :** sexe · âge · taille · planning du jour · préférences vestimentaires · morphologie · météo et lieu

---

## Table des matières

1. [Architecture](#architecture)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Entraînement du modèle](#entraînement-du-modèle)
5. [Lancer l'API](#lancer-lapi)
6. [Interface Web de test](#interface-web-de-test)
7. [Liaison API avec l'application](#liaison-api-avec-lapplication-magicmirrorflutter)
8. [Contrat de réponse](#contrat-de-réponse-recommandation)
9. [Mode intégration automatique](#mode-intégration-automatique-direct-application)
10. [Mode fichier local](#si-tu-nas-pas-encore-dapi-magicmirror)
11. [Identification faciale](#identification-faciale-caméra-pour-miroir-intelligent)
12. [Recommandation depuis contexte réel](#recommandation-depuis-contexte-réel-agenda--météo)
13. [Exemple d'appel manuel](#exemple-dappel-manuel)
14. [Collecte feedback](#collecte-feedback-données-réelles)
15. [Entraînement avec données réelles](#entraînement-avec-données-réelles)
16. [Limites et suite](#limites-et-suite)
17. [À propos](#à-propos)

---

## Architecture

Le système est composé de 3 parties :

### 1. Détection de morphologie
Si l'utilisateur fournit ses mesures (épaules, taille, hanches), la morphologie est déduite automatiquement.

### 2. Scoring ML de tenue
Un modèle de classification binaire évalue la compatibilité utilisateur / contexte / tenue. Les tenues sont triées par probabilité de pertinence.

### 3. API de recommandation
Endpoint FastAPI qui retourne un top-k de tenues.

---

## Prérequis

- Python 3.11+

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Entraînement du modèle

```bash
python -m src.outfit_ml.train --samples 4000
```

**Fichiers produits :**

```
models/
├── outfit_ranker.joblib
└── outfit_ranker_metrics.json
```

**Validation du dataset avant entraînement** *(recommandé)* :

```bash
python -m src.outfit_ml.validate_dataset --dataset-root data/dataset
```

**Conversion CSV → Parquet partitionné par date :**

```bash
python -m src.outfit_ml.export_parquet \
  --dataset-root data/dataset \
  --output-root data/parquet
```

---

## Lancer l'API

**Option recommandée avec `.env` :**

```bash
cp .env.example .env
# Édite .env et renseigne tes vraies valeurs
uvicorn src.outfit_ml.api:app --reload
```

L'API charge automatiquement les variables depuis `.env`.

**Option via export shell :**

```bash
export OPENWEATHER_API_KEY="ta_cle_openweather"
uvicorn src.outfit_ml.api:app --reload
```

---

## Interface Web de test

URL : `http://127.0.0.1:8000/ui`

| Mode | Endpoint appelé |
|---|---|
| Manuel | `POST /recommend` |
| Auto | `POST /recommend/auto` |

L'interface permet de :

- saisir les champs du profil et du contexte
- envoyer une clé API via `X-API-Key` si `API_AUTH_ENABLED=true`
- visualiser les suggestions et la réponse JSON brute
- consulter un dashboard technique via `GET /dashboard/technical` *(état service, source de données, métriques modèle, stats feedback)*

> En mode auto, les champs météo manuels sont masqués et les détails OpenWeather sont affichés dans les résultats.

---

## Liaison API avec l'application (MagicMirror/Flutter)

Le service expose une API FastAPI consommée directement par l'application.

**Configuration minimale recommandée dans `.env` :**

```env
API_AUTH_ENABLED=true
API_AUTH_KEY=replace_with_strong_shared_secret
ALLOWED_ORIGINS=https://your-magicmirror-app.example.com
```

L'application doit envoyer l'en-tête HTTP suivant :

```
X-API-Key: replace_with_strong_shared_secret
```

**Endpoint principal recommandé côté application :**

```
POST /mirror/recommend-from-camera
```

Ce endpoint couvre le flux complet : identification + contexte + recommandations.

---

## Contrat de réponse (recommandation)

Les réponses de recommandation incluent :

| Champ | Description |
|---|---|
| `suggestions` | Top-k tenues avec score et raisons |
| `inferred_body_shape` | Morphologie déduite |
| `dominant_occasion` | Occasion principale détectée |
| `weather_bucket` | Bucket météo utilisé |
| `resolved_context.source` | `manual` · `context` · `auto` |
| `resolved_context.location` | Lieu effectif |
| `resolved_context.weather` | Température + condition utilisées |
| `resolved_context.agenda_labels` | Labels agenda interprétés |
| `resolved_context.openweather` | Ville, pays, ressenti, humidité, vent *(flux `context` et `auto`)* |

**Exemple minimal de `resolved_context` :**

```json
{
  "source": "auto",
  "location": "Lyon",
  "weather": {
    "temperature_c": 18.3,
    "condition": "clear"
  },
  "agenda_labels": ["work", "meeting"],
  "openweather": {
    "city": "Lyon",
    "country": "FR",
    "temperature_c": 18.3,
    "feels_like_c": 17.8,
    "humidity_percent": 52,
    "condition": "Clear",
    "description": "clear sky",
    "wind_speed_m_s": 2.7
  }
}
```

---

## Mode intégration automatique (direct application)

Configure les variables de ton API backend :

```env
MAGICMIRROR_API_BASE_URL=https://ton-app.example.com
MAGICMIRROR_API_TOKEN=token_optionnel
MAGICMIRROR_PROFILE_PATH_TEMPLATE=/api/users/{user_id}/profile
MAGICMIRROR_AGENDA_PATH_TEMPLATE=/api/users/{user_id}/agenda/today
```

**Appel minimal :**

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "location": "Lyon",
    "top_k": 3
  }'
```

**Avec overrides** *(prioritaires sur le profil récupéré)* :

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u-001",
    "location": "Lyon",
    "gender": "female",
    "age": 29,
    "top_size": "m",
    "bottom_size": "m",
    "shoe_size": "40",
    "style_preferences": ["minimalist", "elegant"],
    "agenda": ["work", "meeting"],
    "top_k": 3
  }'
```

Dans ce mode, le service effectue automatiquement :

1. Lecture du profil utilisateur (sexe, âge, taille, préférences, morphologie)
2. Lecture de l'agenda du jour depuis l'application
3. Récupération de la météo via OpenWeather
4. Recommandation top-k sans payload manuel complexe

---

## Si tu n'as pas encore d'API MagicMirror

Tu peux fonctionner en **mode fichier local** immédiatement.

**1. Utiliser les fichiers JSON locaux :**

```
data/users/u-001/
├── profile.json
└── agenda_today.json
```

**2. Configurer `.env` :**

```env
MAGICMIRROR_DATA_SOURCE=file
OPENWEATHER_API_KEY=ta_cle_openweather
MAGICMIRROR_PROFILE_FILE_TEMPLATE=data/users/{user_id}/profile.json
MAGICMIRROR_AGENDA_FILE_TEMPLATE=data/users/{user_id}/agenda_today.json
```

**3. Appeler le endpoint auto :**

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u-001", "top_k": 3}'
```

> Quand ton API backend sera disponible, il suffira de passer `MAGICMIRROR_DATA_SOURCE=api`.

---

## Identification faciale (caméra pour miroir intelligent)

Le projet inclut un module local d'identification faciale : enrôlement d'un visage et identification depuis une image caméra.

**Configuration :**

```bash
pip install face-recognition
export FACE_REGISTRY_PATH=data/vision/face_registry.json
```

> ⚠️ **Recommandations production :** utiliser uniquement sur consentement explicite, conserver les données en local (pas d'envoi cloud), ajouter un anti-spoofing (liveness) avant de valider l'identité.

### Endpoints vision

**`POST /vision/enroll`** — Enrôler un utilisateur :

```json
{
  "user_id": "u-001",
  "image_base64": "data:image/jpeg;base64,..."
}
```

**`POST /vision/identify`** — Identifier un visage :

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "threshold": 0.45,
  "max_results": 1
}
```

### Endpoint unique Android / Web / Webcam

**`POST /mirror/recommend-from-camera`** — Flux complet en une seule requête après capture caméra :

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "location": "Lyon",
  "threshold": 0.45,
  "top_k": 3
}
```

Ce endpoint enchaîne automatiquement :

1. Identification faciale
2. Récupération du profil + agenda du jour
3. Récupération météo OpenWeather
4. Retour des suggestions de tenue

---

## Recommandation depuis contexte réel (agenda + météo)

Utilise cet endpoint quand l'application dispose déjà des données agenda. La météo est récupérée automatiquement via OpenWeather à partir de `location`.

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

---

## Exemple d'appel manuel

**`POST /recommend`** — avec profil et contexte complets :

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

---

## Collecte feedback (données réelles)

**Endpoints disponibles :**

| Endpoint | Description |
|---|---|
| `POST /feedback/event` | Loguer un événement unique |
| `POST /feedback/batch` | Loguer une session complète |
| `POST /feedback/events` | Variante batch |
| `GET /feedback/stats` | Consulter le volume et la répartition |

**Types d'événements :** `impression` · `click` · `selected` · `dismissed`

**Exemple d'événement unitaire :**

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

**Exemple batch (session complète en un appel) :**

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

---

## Entraînement avec données réelles

Le trainer utilise les feedbacks réels et bascule automatiquement sur le synthétique si le volume est insuffisant.

```bash
python -m src.outfit_ml.train \
  --prefer-real-data \
  --real-feedback-log data/feedback/events.jsonl \
  --min-real-samples 200 \
  --split-mode time
```

**Métriques supplémentaires** si `session_id` est présent :

`precision_at_3` · `recall_at_3` · `ndcg_at_3`

---

## Limites et suite

| Limite | Action recommandée |
|---|---|
| Dataset d'entraînement synthétique | Remplacer par de vraies interactions utilisateurs (feedback implicite/explicite) |
| Météo et agenda simulés | Intégrer une source météo réelle et l'agenda MagicMirror |

---

## À propos

Développeur : [josoavj](https://github.com/josoavj)