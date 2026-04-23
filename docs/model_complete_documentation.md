# Documentation du modèle ML

> Système de recommandation de tenues — pipeline complet d'entraînement et d'inférence.

---

## Table des matières

1. [But du modèle](#1-but-du-modèle)
2. [Architecture globale](#2-architecture-globale)
3. [Données d'entraînement](#3-données-dentraînement)
4. [Features du modèle](#4-features-du-modèle)
5. [Modèles candidats et hyperparamètres](#5-modèles-candidats-et-hyperparamètres)
6. [Pipeline d'entraînement](#6-pipeline-dentraînement)
7. [Métriques et interprétation](#7-métriques-et-interprétation)
8. [Inférence et ranking](#8-inférence-et-ranking)
9. [Paramètres fonctionnels](#9-paramètres-fonctionnels)
10. [Mappings métier](#10-mappings-métier)
11. [Performance et tuning](#11-performance-et-tuning)
12. [Limites actuelles](#12-limites-actuelles)
13. [Roadmap recommandée](#13-roadmap-recommandée)
14. [Fichiers de référence](#14-fichiers-de-référence)
15. [Commandes utiles](#15-commandes-utiles)
16. [Pipeline feedback réel](#16-pipeline-feedback-réel)

---

## 1. But du modèle

Le modèle prédit la **pertinence d'une tenue** pour un utilisateur dans un contexte donné.

Le contexte combine :

| Dimension | Détail |
|---|---|
| **Profil utilisateur** | Sexe, âge, taille, préférences, morphologie |
| **Tailles** | Haut, bas, chaussures |
| **Contexte journée** | Agenda |
| **Contexte externe** | Météo |
| **Tenue** | Style, occasion, compatibilité |

**Sorties :**

- un score de compatibilité par tenue
- un classement top-k des tenues recommandées

---

## 2. Architecture globale

La solution comporte deux couches.

### Couche 1 — Contextuelle

- Normalisation agenda → occasion dominante
- Conversion météo brute → bucket météo
- Inférence de morphologie à partir des mensurations

### Couche 2 — ML de ranking

- Modèle de classification binaire (pipeline scikit-learn)
- Évaluation de la probabilité positive par tenue
- Tri descendant des probabilités

### Fichiers clefs

```
src/outfit_ml/
├── features.py
├── data.py
├── train.py
└── recommend.py
```

---

## 3. Données d'entraînement

Le dataset d'entraînement est **synthétique** (bootstrapping), généré dans `src/outfit_ml/data.py`.

> ⚠️ Ce schéma donne un jeu exploitable rapidement, mais ne remplace pas des données réelles de production.

### 3.1 Variables simulées

| Variable | Valeurs |
|---|---|
| `age` | Entier [16, 65] |
| `height_cm` | Entier [150, 200] |
| `gender` | `female` · `male` · `non_binary` |
| `top_size` / `bottom_size` | `xs` · `s` · `m` · `l` · `xl` · `xxl` · `unknown` |
| `shoe_size` | Valeur numérique simulée puis bucketisée |
| `body_shape` | `hourglass` · `rectangle` · `pear` · `inverted_triangle` · `oval` |
| `occasion` | `work` · `meeting` · `casual` · `sport` · `event` · `date` · `outdoor` |
| `weather` | `cold` · `mild` · `hot` · `rainy` |
| `style_preferences` | 1 à 2 styles parmi : `classic` `minimalist` `casual` `sport` `elegant` `practical` |

### 3.2 Construction du label

La cible binaire `label` est dérivée d'un signal pondéré :

```
signal = 0.35 × style_match
       + 0.25 × occasion_match
       + 0.20 × weather_match
       + 0.10 × shape_match
       + 0.07 × gender_match
       + 0.03 × top_size_match
       + 0.03 × bottom_size_match
       + 0.03 × shoe_size_match
```

Puis :

- `noisy_threshold` = `0.55` ± bruit uniforme dans `[−0.08, +0.08]`
- `label = 1` si `signal >= noisy_threshold`, sinon `0`

---

## 4. Features du modèle

Les features sont définies dans `src/outfit_ml/train.py`.

### 4.1 Features catégorielles

Encodage : `OneHotEncoder(handle_unknown="ignore")`

`gender` · `body_shape` · `occasion` · `weather` · `outfit_id` · `top_size` · `bottom_size` · `shoe_bucket`

### 4.2 Features numériques

**Profil :** `age` · `height_cm`

**Signaux de matching :** `style_match` · `occasion_match` · `weather_match` · `shape_match` · `gender_match` · `top_size_match` · `bottom_size_match` · `shoe_size_match`

**Préférences utilisateur :** `pref_classic` · `pref_minimalist` · `pref_casual` · `pref_sport` · `pref_elegant` · `pref_practical`

**Styles tenue :** `outfit_style_classic` · `outfit_style_minimalist` · `outfit_style_casual` · `outfit_style_sport` · `outfit_style_elegant` · `outfit_style_practical`

---

## 5. Modèles candidats et hyperparamètres

> Sélection automatique du meilleur modèle selon **ROC-AUC** sur split validation.

### 5.1 `RandomForestClassifier`

| Paramètre | Valeur |
|---|---|
| `n_estimators` | 350 |
| `max_depth` | 14 |
| `class_weight` | `balanced_subsample` |
| `random_state` | 42 |
| `n_jobs` | -1 |

### 5.2 `ExtraTreesClassifier`

| Paramètre | Valeur |
|---|---|
| `n_estimators` | 450 |
| `max_depth` | `None` |
| `class_weight` | `balanced` |
| `random_state` | 42 |
| `n_jobs` | -1 |

---

## 6. Pipeline d'entraînement

**Implémentation :** `src/outfit_ml/train.py`

**Étapes :**

1. Chargement du catalogue tenues
2. Génération du dataset synthétique
3. Split train/test stratifié (80/20)
4. Entraînement des modèles candidats
5. Évaluation des métriques
6. Sélection du meilleur selon ROC-AUC
7. Sauvegarde du pipeline et des métriques

**Commande standard :**

```bash
python -m src.outfit_ml.train --samples 4000
```

**Fichiers produits :**

```
models/
├── outfit_ranker.joblib
└── outfit_ranker_metrics.json
```

---

## 7. Métriques et interprétation

### Résultats actuels (`models/outfit_ranker_metrics.json`)

| Métrique | Valeur |
|---|---|
| `best_model` | `random_forest` |
| `roc_auc` | **0.9882** |
| `average_precision` | **0.9881** |
| `precision` | 0.9024 |
| `recall` | 0.9571 |
| `f1` | 0.9289 |
| `samples` | 4 000 |

**Interprétation :**

- ROC-AUC et AP élevés → bonne séparation sur données synthétiques
- recall > precision → le modèle favorise la récupération des tenues pertinentes

---

## 8. Inférence et ranking

**Implémentation :** `src/outfit_ml/recommend.py`

**Étapes runtime :**

1. Inférence morphologie si non fournie
2. Dérivation occasion dominante depuis l'agenda
3. Bucket météo
4. Construction d'une ligne de features par tenue du catalogue (tailles + signaux de matching)
5. `predict_proba` sur chaque ligne
6. Tri descendant des scores
7. Retour top-k avec raisons explicatives + contexte résolu

**Raisons explicatives (règles simples) :**

- Correspond aux préférences de style
- Adapté à la météo
- Cohérent avec l'agenda
- Bonne compatibilité globale

---

## 9. Paramètres fonctionnels

### 9.1 Paramètres d'entraînement

| Paramètre | Description |
|---|---|
| `--samples` | Taille du dataset synthétique |
| `--catalog` | Chemin catalogue tenues |
| `--output` | Chemin modèle `.joblib` |
| `--metrics-output` | Chemin métriques JSON |
| `--model-candidates` | Liste des modèles à comparer |

### 9.2 Paramètres d'inférence

**`POST /recommend`**

`user_id` · `gender` · `age` · `height_cm` · `style_preferences` · `body_shape` *(optionnel)* · `body_measurements` *(optionnel)* · `agenda` · `location` · `weather.temperature_c` · `weather.condition` · `top_k`

**`POST /recommend/auto`**

`user_id` · `location` *(optionnelle)* · overrides optionnels : `gender` `age` `height_cm` `clothing_size` `top_size` `bottom_size` `shoe_size` `style_preferences` `body_shape` `body_measurements` `agenda` · `top_k`

**`POST /mirror/recommend-from-camera`**

`image_base64` · `location` *(optionnelle)* · `threshold` *(identification faciale)* · `top_k`

> Les trois endpoints renvoient également un objet `resolved_context` : source, location et météo effectives, agenda interprété, détails OpenWeather.

---

## 10. Mappings métier

### 10.1 Morphologie (`features.py`)

Règles basées sur ratios épaules/hanches et taille/hanches :

`hourglass` · `pear` · `inverted_triangle` · `oval` · `rectangle` · `unknown` *(si données absentes)*

### 10.2 Météo → bucket

| Condition | Bucket |
|---|---|
| Pluie détectée | `rainy` |
| Température < 10°C | `cold` |
| Température > 24°C | `hot` |
| Sinon | `mild` |

### 10.3 Agenda → occasion dominante

| Mots-clés détectés | Occasion |
|---|---|
| Réunion, bureau… | `work` |
| Sport, gym… | `sport` |
| Dîner, romantique… | `date` |
| Soirée, gala… | `event` |
| Randonnée, parc… | `outdoor` |
| *(aucun match)* | `casual` |

---

## 11. Performance et tuning

### Actions recommandées

1. **Remplacer le dataset synthétique** par des interactions réelles
   - Feedback explicite : like/dislike
   - Feedback implicite : clic, durée de visualisation, tenue effectivement portée

2. **Nouvelles features**
   - Saison
   - Pluie probable sur plage horaire
   - Formalité précise des événements agenda
   - Contraintes vestimentaires d'entreprise
   - Historique personnel de satisfaction

3. **Tuning des hyperparamètres**
   - Recherche sur `n_estimators`, `max_depth`, `min_samples_leaf`
   - Calibrage probabiliste (Platt / Isotonic)

4. **Évaluation offline plus robuste**
   - Validation croisée temporelle si données datées
   - Métriques top-k : Precision@k, Recall@k, NDCG

5. **Monitoring production**
   - Drift des distributions
   - Performance par segment (âge, style, météo)
   - Taux de non-reconnaissance caméra

---

## 12. Limites actuelles

| Limite | Détail |
|---|---|
| Données synthétiques | Pas de signal utilisateur réel |
| Morphologie simplifiée | Heuristiques basées sur ratios |
| Explications rule-based | Pas de SHAP / LIME |
| Pas de ré-entraînement online | Pipeline statique |
| Boucle de feedback inactive | Non encore activée |

---

## 13. Roadmap recommandée

### Version 1 *(actuelle)*

- Pipeline opérationnel complet
- Intégration caméra + recommandation

### Version 2

- Collecte feedback utilisateur
- Recalibration des scores
- Segmentation des modèles par contexte

### Version 3

- Personnalisation avancée
- Apprentissage continu
- Governance ML complète (monitoring, A/B tests, rollback)

---

## 14. Fichiers de référence

```
src/outfit_ml/
├── train.py
├── data.py
├── features.py
├── recommend.py
├── context.py
└── api.py

models/
└── outfit_ranker_metrics.json

docs/
├── quickstart.md
└── flutter_android_integration.md
```

---

## 15. Commandes utiles

**Entraînement :**

```bash
python -m src.outfit_ml.train --samples 4000
```

**Vérification de compilation :**

```bash
~/.pyenv/bin/python -m compileall src
```

**Lancement de l'API :**

```bash
uvicorn src.outfit_ml.api:app --reload
```

---

## 16. Pipeline feedback réel

### Collecte des interactions

```bash
POST /feedback/event   # Loguer impression / click / selected / dismissed
GET  /feedback/stats   # Vérifier le volume et la répartition
```

**Format de stockage :** JSON Lines dans `data/feedback/events.jsonl`
*(configurable via `FEEDBACK_LOG_PATH`)*

### Transformation en dataset d'entraînement

- Groupement par `session_id`
- Positif : `selected` (et `click`)
- Négatif : tenues en `impression` non sélectionnées
- Recalcul des features de matching depuis le catalogue

### Activation de l'entraînement réel

```bash
python -m src.outfit_ml.train \
  --prefer-real-data \
  --real-feedback-log data/feedback/events.jsonl \
  --split-mode time
```

> **Fallback automatique :** si le volume réel est insuffisant (`< --min-real-samples`) ou si les classes ne sont pas exploitables, le pipeline bascule sur le dataset synthétique.