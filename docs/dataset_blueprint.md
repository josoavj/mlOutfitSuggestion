# Dataset Blueprint Complet

## Objectif

Ce blueprint définit un dataset structuré pour entraîner un modèle fiable et précis de recommandation de tenues.

Le schéma est decoupé en 5 tables:

- users
- outfits_catalog
- context_sessions
- recommendation_impressions
- interactions

## Format recommandé

- Format de travail: CSV (simple et interoperable)
- Format production: Parquet partitionné par date
- Encodage: UTF-8
- Délimiteur multi-valeurs: `|` (ex: `casual|minimalist`)

## 1. users.csv

| colonne | type | exemple | obligatoire | description |
|---|---|---|---|---|
| user_id | string | u-001 | oui | identifiant unique utilisateur |
| gender | enum | female | oui | female/male/non_binary/unknown |
| age | int | 29 | oui | age utilisateur |
| height_cm | int | 168 | oui | taille en cm |
| body_shape | enum | hourglass | oui | morphologie |
| clothing_size | enum | m | oui | taille generale |
| top_size | enum | m | oui | taille haut |
| bottom_size | enum | m | oui | taille bas |
| shoe_size | string | 40 | oui | pointure |
| style_preferences | string(list) | minimalist|elegant | oui | styles favoris |
| location_home | string | Lyon | oui | ville de reference |
| updated_at | datetime | 2026-04-09T08:10:00Z | oui | date de maj |

## 2. outfits_catalog.csv

| colonne | type | exemple | obligatoire | description |
|---|---|---|---|---|
| outfit_id | string | smart_casual | oui | id tenue |
| label | string | Smart Casual | oui | nom affichable |
| styles | string(list) | casual|minimalist | oui | styles associes |
| occasions | string(list) | work|casual | oui | contextes d'usage |
| weather_compatibility | string(list) | mild|hot | oui | meteo compatible |
| fit_profiles | string(list) | hourglass|rectangle | oui | morphologies compatibles |
| formality_level | string | business | oui | niveau de formalite |
| season | string | spring | oui | saison principale |

## 3. context_sessions.csv

| colonne | type | exemple | obligatoire | description |
|---|---|---|---|---|
| session_id | string | s-20260409-001 | oui | id session reco |
| user_id | string | u-001 | oui | utilisateur |
| timestamp | datetime | 2026-04-09T08:15:00Z | oui | horodatage session |
| location | string | Lyon | oui | localisation session |
| weather_bucket | enum | rainy | oui | cold/mild/hot/rainy |
| temperature_c | float | 14.2 | oui | temperature |
| agenda_labels | string(list) | work|meeting | oui | labels agenda |
| camera_confidence | float | 0.92 | oui | confiance identification |

## 4. recommendation_impressions.csv

| colonne | type | exemple | obligatoire | description |
|---|---|---|---|---|
| session_id | string | s-20260409-001 | oui | session |
| user_id | string | u-001 | oui | utilisateur |
| outfit_id | string | smart_casual | oui | tenue affichee |
| rank_position | int | 0 | oui | position dans le top-k |
| score_model | float | 0.8732 | oui | score predit |
| shown_at | datetime | 2026-04-09T08:15:01Z | oui | horodatage impression |

## 5. interactions.csv

| colonne | type | exemple | obligatoire | description |
|---|---|---|---|---|
| session_id | string | s-20260409-001 | oui | session |
| user_id | string | u-001 | oui | utilisateur |
| outfit_id | string | smart_casual | oui | tenue |
| event_type | enum | selected | oui | impression/click/selected/dismissed |
| event_time | datetime | 2026-04-09T08:15:11Z | oui | horodatage action |
| dwell_time_ms | int | 5400 | oui | temps engagement |

## Labels d'entrainement recommandes

- Positif (label=1): `selected`
- Negatif (label=0): `impression` sans `selected` dans la meme session
- Option: `click` peut etre positif faible selon regle metier

## Validation automatique du contrat

Le projet contient un validateur:

```bash
python -m src.outfit_ml.validate_dataset --dataset-root data/dataset
```

Sortie:

- `data/quality/validation_report.json`
- statut PASS/FAIL

Contrôles réalisés:

- colonnes obligatoires
- taux de null par colonne
- doublons sur cles primaires indicatives
- valeurs invalides sur enums critiques

## Exigences qualite minimales (conseillees)

- Null rate <= 5% sur chaque colonne obligatoire
- 0 doublon sur cles indicatives
- 0 valeur hors vocabulaire sur enums critiques
- split temporel train/test pour evaluation realiste

## Strategie de stockage

1. Ingestion quotidienne en CSV
2. Conversion periodique en Parquet partitionne (`date=YYYY-MM-DD`)
3. Validation du contrat avant chaque entrainement
4. Archivage des rapports de qualite par run

## Conversion CSV -> Parquet partitionne

Script fourni:

```bash
python -m src.outfit_ml.export_parquet --dataset-root data/dataset --output-root data/parquet
```

Règles de partition:

- users: partition par `updated_at`
- context_sessions: partition par `timestamp`
- recommendation_impressions: partition par `shown_at`
- interactions: partition par `event_time`
- outfits_catalog: fichier parquet non partitionne

Structure de sortie typique:

```text
data/parquet/
	users/
		partition_date=2026-04-09/
	context_sessions/
		partition_date=2026-04-09/
	recommendation_impressions/
		partition_date=2026-04-09/
	interactions/
		partition_date=2026-04-09/
	outfits_catalog/
		outfits_catalog.parquet
```
