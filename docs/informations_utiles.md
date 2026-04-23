# Guide opérationnel

> Référence rapide pour déployer, configurer et maintenir le pipeline ML de recommandation de tenues.

---

## Table des matières

1. [Démarrage rapide](#démarrage-rapide)
2. [Variables d'environnement](#variables-denvironnement-essentielles)
3. [Endpoints principaux](#endpoints-principaux)
4. [Workflow recommandé en production](#workflow-recommandé-en-production)
5. [Commandes utiles](#commandes-utiles)
6. [Critères qualité des données](#critères-qualité-des-données)
7. [Métriques à surveiller](#métriques-à-surveiller)
8. [Dépannage rapide](#dépannage-rapide)
9. [Documentation associée](#documentation-associée)

---

## Démarrage rapide

```bash
# 1. Installer les dépendances
~/.pyenv/bin/python -m pip install -r requirements.txt

# 2. Entraîner le modèle
~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000

# 3. Lancer l'API
uvicorn src.outfit_ml.api:app --reload
```

---

## Variables d'environnement essentielles

### Générales

| Variable | Description |
|---|---|
| `OPENWEATHER_API_KEY` | Clé OpenWeather |
| `MAGICMIRROR_DATA_SOURCE` | Source de données : `api` · `file` · `supabase` |
| `FACE_REGISTRY_PATH` | Registre local des embeddings visage |
| `FEEDBACK_LOG_PATH` | Journal JSONL des interactions |
| `API_AUTH_ENABLED` / `API_AUTH_KEY` | Protection des endpoints ML |
| `ALLOWED_ORIGINS` | Liste blanche CORS des clients |

### Mode `api`

| Variable | Description |
|---|---|
| `MAGICMIRROR_API_BASE_URL` | URL de base du backend applicatif |
| `MAGICMIRROR_PROFILE_PATH_TEMPLATE` | Route profil utilisateur |
| `MAGICMIRROR_AGENDA_PATH_TEMPLATE` | Route agenda utilisateur |

### Mode `file`

| Variable | Description |
|---|---|
| `MAGICMIRROR_PROFILE_FILE_TEMPLATE` | Chemin vers le fichier profil |
| `MAGICMIRROR_AGENDA_FILE_TEMPLATE` | Chemin vers le fichier agenda |

### Mode `supabase`

| Variable | Description |
|---|---|
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` ou `SUPABASE_ANON_KEY` | Clé d'accès |
| `SUPABASE_PROFILE_TABLE` | Nom de la table profils |
| `SUPABASE_PROFILE_USER_ID_COLUMN` | Colonne identifiant utilisateur |
| `SUPABASE_AGENDA_TABLE` | Nom de la table agenda |
| `SUPABASE_AGENDA_USER_ID_COLUMN` | Colonne identifiant utilisateur |
| `SUPABASE_AGENDA_DATE_COLUMN` | Colonne date |
| `SUPABASE_AGENDA_TITLE_COLUMN` | Colonne titre |
| `SUPABASE_AGENDA_CATEGORY_COLUMN` | Colonne catégorie |
| `SUPABASE_AGENDA_TAGS_COLUMN` | Colonne tags |

---

## Endpoints principaux

### Santé & recommandation

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | État du service |
| `POST` | `/recommend` | Recommandation manuelle (profil + contexte complets) |
| `POST` | `/recommend/context` | Recommandation avec agenda intégré + météo auto |
| `POST` | `/recommend/auto` | Recommandation entièrement automatique |
| `POST` | `/mirror/recommend-from-camera` | Flux complet : identification + contexte + recommandations |

### Vision

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/vision/enroll` | Enrôler un visage utilisateur |
| `POST` | `/vision/identify` | Identifier un visage depuis une image |

### Feedback

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/feedback/event` | Loguer un événement unique |
| `POST` | `/feedback/events` | Loguer une session complète (batch) |
| `GET` | `/feedback/stats` | Consulter le volume et la répartition |

---

## Workflow recommandé en production

1. Activer l'authentification API (en-tête `X-API-Key`).
2. Identifier l'utilisateur via caméra : `POST /mirror/recommend-from-camera`.
3. Afficher le top-k de tenues recommandées.
4. Journaliser les impressions et actions via `POST /feedback/events`.
5. Vérifier la qualité des données avant tout ré-entraînement.
6. Ré-entraîner avec `--prefer-real-data`.
7. Exporter en Parquet pour le stockage analytique.

---

## Commandes utiles

**Validation du dataset :**

```bash
~/.pyenv/bin/python -m src.outfit_ml.validate_dataset \
  --dataset-root data/dataset
```

**Entraînement sur données réelles** *(fallback automatique sur synthétique si volume insuffisant)* :

```bash
~/.pyenv/bin/python -m src.outfit_ml.train \
  --prefer-real-data \
  --real-feedback-log data/feedback/events.jsonl \
  --min-real-samples 200 \
  --split-mode time
```

**Export Parquet partitionné par date :**

```bash
~/.pyenv/bin/python -m src.outfit_ml.export_parquet \
  --dataset-root data/dataset \
  --output-root data/parquet
```

---

## Critères qualité des données

| Critère | Règle |
|---|---|
| Colonnes obligatoires | Présentes dans les 5 tables |
| Taux de valeurs nulles | ≤ 5 % sur les colonnes obligatoires |
| Doublons | 0 sur les clés indicatives |
| `event_type` | `impression` · `click` · `selected` · `dismissed` |
| `weather_bucket` | `cold` · `mild` · `hot` · `rainy` |
| Tailles | Normalisées : `xs` · `s` · `m` · `l` · `xl` · `xxl` · `unknown` |

---

## Métriques à surveiller

### Métriques offline

| Métrique | Description |
|---|---|
| `roc_auc` | Qualité de séparation globale |
| `average_precision` | Précision moyenne sur toutes les seuils |
| `precision` / `recall` / `f1` | Métriques de classification standard |
| `precision_at_3` | Précision dans les 3 premières suggestions |
| `recall_at_3` | Rappel dans les 3 premières suggestions |
| `ndcg_at_3` | Qualité du classement top-3 |

### Métriques online

| Métrique | Description |
|---|---|
| Taux de sélection top-3 | Part des sessions avec une tenue choisie |
| CTR recommandations | Taux de clic sur les suggestions |
| Taux de non-reconnaissance caméra | Échecs d'identification faciale |
| Latence API p95 | Temps de réponse au 95e percentile |

---

## Dépannage rapide

| Erreur | Solution |
|---|---|
| `pyarrow` manquant | `~/.pyenv/bin/python -m pip install "pyarrow>=19.0.1,<20.0.0"` |
| Vision non activée (`501`) | `~/.pyenv/bin/python -m pip install face-recognition` |
| Pas assez de données réelles | Le trainer bascule automatiquement sur le dataset synthétique |

---

## Documentation associée

| Fichier | Contenu |
|---|---|
| [`docs/quickstart.md`](docs/quickstart.md) | Guide de démarrage complet |
| [`docs/flutter_android_integration.md`](docs/flutter_android_integration.md) | Intégration Flutter Android |
| [`docs/model_complete_documentation.md`](docs/model_complete_documentation.md) | Documentation complète du modèle ML |
| [`docs/dataset_blueprint.md`](docs/dataset_blueprint.md) | Structure et schéma du dataset |