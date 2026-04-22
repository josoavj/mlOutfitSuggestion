# Informations Utiles (Guide Operationnel)

## Démarrage rapide

1. Installer les dépendances:

- ~/.pyenv/bin/python -m pip install -r requirements.txt

2. Entraîner le modèle:

- ~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000

3. Lancer l'API:

- uvicorn src.outfit_ml.api:app --reload

## Variables d'environnement essentielles

- OPENWEATHER_API_KEY: cle OpenWeather
- MAGICMIRROR_DATA_SOURCE: api, file ou supabase
- MAGICMIRROR_API_BASE_URL: base URL backend app (si mode api)
- MAGICMIRROR_PROFILE_PATH_TEMPLATE: route profil user
- MAGICMIRROR_AGENDA_PATH_TEMPLATE: route agenda user
- MAGICMIRROR_PROFILE_FILE_TEMPLATE: fichier profil (si mode file)
- MAGICMIRROR_AGENDA_FILE_TEMPLATE: fichier agenda (si mode file)
- FACE_REGISTRY_PATH: registre local embeddings visage
- FEEDBACK_LOG_PATH: journal JSONL des interactions
- API_AUTH_ENABLED / API_AUTH_KEY: protection des endpoints ML
- ALLOWED_ORIGINS: whitelist CORS des clients

Variables Supabase (si mode supabase):

- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY
- SUPABASE_PROFILE_TABLE / SUPABASE_PROFILE_USER_ID_COLUMN
- SUPABASE_AGENDA_TABLE / SUPABASE_AGENDA_USER_ID_COLUMN / SUPABASE_AGENDA_DATE_COLUMN
- SUPABASE_AGENDA_TITLE_COLUMN / SUPABASE_AGENDA_CATEGORY_COLUMN / SUPABASE_AGENDA_TAGS_COLUMN

## Endpoints principaux

- GET /health
- POST /recommend
- POST /recommend/context
- POST /recommend/auto
- POST /mirror/recommend-from-camera

**Vision:**

- POST /vision/enroll
- POST /vision/identify

**Feedback:**

- POST /feedback/event
- POST /feedback/events
- GET /feedback/stats

## Workflow recommande en production

1. Auth API activee (entete X-API-Key).
2. Identification utilisateur (camera) via /mirror/recommend-from-camera.
3. Affichage top-k tenues.
4. Journaliser les impressions et actions avec /feedback/events.
5. Vérifier la qualité de données avant ré-entraînement.
6. Re-entrainer avec prefer-real-data.
7. Exporter en Parquet pour un stockage analytique.

## Commandes utiles

**Validation dataset:**

- `~/.pyenv/bin/python -m src.outfit_ml.validate_dataset --dataset-root data/dataset`

**Entraînement sur données réelles (fallback auto):**

- `~/.pyenv/bin/python -m src.outfit_ml.train --prefer-real-data --real-feedback-log data/feedback/events.jsonl --min-real-samples 200 --split-mode time`

**Export Parquet partitionné:**

- `~/.pyenv/bin/python -m src.outfit_ml.export_parquet --dataset-root data/dataset --output-root data/parquet`

## Critiques qualite de données

- Colonnes obligatoires présentes dans les 5 tables.
- Null rate <= 5% sur colonnes obligatoires.
- Doublons = 0 sur clés indicatives.
- event_type dans impression/click/selected/dismissed.
- weather_bucket dans cold/mild/hot/rainy.
- tailles normalisées: xs/s/m/l/xl/xxl/unknown.

## Métriques à surveiller

**Offline:**

- roc_auc
- average_precision
- precision
- recall
- f1
- precision_at_3
- recall_at_3
- ndcg_at_3

**Online:**

- taux sélection top-3
- CTR recommandations
- taux de non-reconnaissance camera
- latence API p95

## Dépannage rapide

**Erreur pyarrow manquant:**

- `~/.pyenv/bin/python -m pip install "pyarrow>=19.0.1,<20.0.0"`

**Erreur vision non activé:**

- `~/.pyenv/bin/python -m pip install face-recognition`

**Pas assez de données réelles:**

- le trainer bascule automatiquement sur le dataset synthétique.

## Liens docs à consulter aussi

- docs/quickstart.md
- docs/flutter_android_integration.md
- docs/model_complete_documentation.md
- docs/dataset_blueprint.md
