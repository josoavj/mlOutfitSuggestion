# Informations Utiles (Guide Operationnel)

## Demarrage rapide

1. Installer les dependances:
- ~/.pyenv/bin/python -m pip install -r requirements.txt

2. Entrainer le modele:
- ~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000

3. Lancer l'API:
- uvicorn src.outfit_ml.api:app --reload

## Variables d'environnement essentielles

- OPENWEATHER_API_KEY: cle OpenWeather
- MAGICMIRROR_DATA_SOURCE: api ou file
- MAGICMIRROR_API_BASE_URL: base URL backend app (si mode api)
- MAGICMIRROR_PROFILE_PATH_TEMPLATE: route profil user
- MAGICMIRROR_AGENDA_PATH_TEMPLATE: route agenda user
- MAGICMIRROR_PROFILE_FILE_TEMPLATE: fichier profil (si mode file)
- MAGICMIRROR_AGENDA_FILE_TEMPLATE: fichier agenda (si mode file)
- FACE_REGISTRY_PATH: registre local embeddings visage
- FEEDBACK_LOG_PATH: journal JSONL des interactions

## Endpoints principaux

- GET /health
- POST /recommend
- POST /recommend/context
- POST /recommend/auto
- POST /mirror/recommend-from-camera

Vision:
- POST /vision/enroll
- POST /vision/identify

Feedback:
- POST /feedback/event
- POST /feedback/events
- GET /feedback/stats

## Workflow recommande en production

1. Identification utilisateur (camera) via /mirror/recommend-from-camera.
2. Affichage top-k tenues.
3. Journaliser les impressions et actions avec /feedback/events.
4. Verifier la qualite de donnees avant re-entrainement.
5. Re-entrainer avec prefer-real-data.
6. Exporter en Parquet pour stockage analytique.

## Commandes utiles

Validation dataset:
- ~/.pyenv/bin/python -m src.outfit_ml.validate_dataset --dataset-root data/dataset

Entrainement sur donnees reelles (fallback auto):
- ~/.pyenv/bin/python -m src.outfit_ml.train --prefer-real-data --real-feedback-log data/feedback/events.jsonl --min-real-samples 200 --split-mode time

Export Parquet partitionne:
- ~/.pyenv/bin/python -m src.outfit_ml.export_parquet --dataset-root data/dataset --output-root data/parquet

## Critiques qualite de donnees

- Colonnes obligatoires presentes dans les 5 tables.
- Null rate <= 5% sur colonnes obligatoires.
- Doublons = 0 sur cles indicatives.
- event_type dans impression/click/selected/dismissed.
- weather_bucket dans cold/mild/hot/rainy.
- tailles normalisees: xs/s/m/l/xl/xxl/unknown.

## Metriques a surveiller

Offline:
- roc_auc
- average_precision
- precision
- recall
- f1
- precision_at_3
- recall_at_3
- ndcg_at_3

Online:
- taux selection top-3
- CTR recommandations
- taux de non-reconnaissance camera
- latence API p95

## Depannage rapide

Erreur pyarrow manquant:
- ~/.pyenv/bin/python -m pip install "pyarrow>=19.0.1,<20.0.0"

Erreur vision non active:
- ~/.pyenv/bin/python -m pip install face-recognition

Pas assez de donnees reelles:
- le trainer bascule automatiquement sur le dataset synthetique.

## Liens docs a lire ensuite

- docs/quickstart.md
- docs/flutter_android_integration.md
- docs/model_complete_documentation.md
- docs/dataset_blueprint.md
