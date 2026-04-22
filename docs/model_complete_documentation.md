# Documentation Complète du Modèle ML

## 1. But du modèle

Le modèle prédit la pertinence d'une tenue pour un utilisateur dans un contexte donné.

Le contexte combine:

- profil utilisateur (sexe, âge, taille, préférences, morphologie)
- tailles utilisateur (taille haut, bas, chaussures)
- contexte journée (agenda)
- contexte externe (meteo)
- metadonnées de la tenue (style, occasion, compatibilité)

Sortie principale:

- un score de compatibilité par tenue
- un classement top-k des tenues recommandées

## 2. Architecture globale

La solution comporte deux couches:

1. Couche contextuelle

- normalisation agenda -> occasion dominante
- conversion météo brute -> bucket météo
- inférence de morphologie a partir de mensurations

2. Couche ML de ranking

- modèle de classification binaire (pipeline scikit-learn)
- évaluation de la probabilité positive par tenue
- tri descendant des probabilités

Fichiers clefs:

- src/outfit_ml/features.py
- src/outfit_ml/data.py
- src/outfit_ml/train.py
- src/outfit_ml/recommend.py

## 3. Donnees d'entrainement

Le dataset d'entrainement est synthétique (bootstrapping), généré dans `src/outfit_ml/data.py`.

### 3.1 Variables simulées

- âge: entier [16, 65]
- height_cm: entier [150, 200]
- gender: female | male | non_binary
- top_size / bottom_size: xs | s | m | l | xl | xxl | unknown
- shoe_size: valeur numerique simulee puis bucketisee
- body_shape: hourglass | rectangle | pear | inverted_triangle | oval
- occasion: work | meeting | casual | sport | event | date | outdoor
- weather: cold | mild | hot | rainy
- style preferences: 1 a 2 styles parmi:
  - classic, minimalist, casual, sport, elegant, practical
- tenue cible: echantillonnee depuis le catalogue configs/outfit_catalog.json

### 3.2 Construction du label

La cible binaire label est derivée d'un signal pondéré:

```text
signal = 0.35 * style_match
  + 0.25 * occasion_match
  + 0.20 * weather_match
  + 0.10 * shape_match
  + 0.07 * gender_match
  + 0.03 * top_size_match
  + 0.03 * bottom_size_match
  + 0.03 * shoe_size_match
```

Puis:

- noisy_threshold = 0.55 +/- bruit uniforme dans [-0.08, +0.08]
- label = 1 si signal >= noisy_threshold, sinon 0

Ce schéma donne un jeu exploitable rapidement, mais ne remplace pas des données réelles de production.

## 4. Features du modèle

Les features sont définies dans `src/outfit_ml/train.py`.

### 4.1 Features categorielles

- gender
- body_shape
- occasion
- weather
- outfit_id
- top_size
- bottom_size
- shoe_bucket

Encodage:

- `OneHotEncoder(handle_unknown="ignore")`

### 4.2 Features numériques

- age
- height_cm
- style_match
- occasion_match
- weather_match
- shape_match
- gender_match
- top_size_match
- bottom_size_match
- shoe_size_match
- pref_classic
- pref_minimalist
- pref_casual
- pref_sport
- pref_elegant
- pref_practical
- outfit_style_classic
- outfit_style_minimalist
- outfit_style_casual
- outfit_style_sport
- outfit_style_elegant
- outfit_style_practical

## 5. Modèles candidats et hyperparamètres

Sélection automatique du meilleur modèle selon ROC-AUC sur split validation.

### 5.1 RandomForestClassifier

- n_estimators = 350
- max_depth = 14
- random_state = 42
- class_weight = balanced_subsample
- n_jobs = -1

### 5.2 ExtraTreesClassifier

- n_estimators = 450
- max_depth = None
- random_state = 42
- class_weight = balanced
- n_jobs = -1

## 6. Pipeline d'entraînement

Implémentation: src/outfit_ml/train.py

**Etapes:**

1. Chargement du catalogue tenues
2. Génération du dataset synthétique
3. Split train/test stratifié (80/20)
4. Entraînement des modèles candidats
5. Evaluation métriques
6. Séléction du meilleur selon ROC-AUC
7. Sauvegarde du pipeline et métriques

**Commande standard:**
```python -m src.outfit_ml.train --samples 4000```

**Fichiers produits:**

- `models/outfit_ranker.joblib`
- `models/outfit_ranker_metrics.json`

## 7. Métriques et interprétation

Métriques calculées:

- roc_auc
- average_precision
- precision
- recall
- f1

Exemple actuel (models/outfit_ranker_metrics.json):

- best_model: random_forest
- roc_auc: 0.9882
- average_precision: 0.9881
- precision: 0.9024
- recall: 0.9571
- f1: 0.9289
- samples: 4000

Interprétation rapide:

- ROC-AUC et AP eleves: bonne séparation sur données synthétiques
- recall > precision: le modèle favorise la recuperation des tenues pertinentes

## 8. Inférence et ranking

Implémentation: src/outfit_ml/recommend.py

Etapes runtime:

1. Inférence morphologie si non fournie
2. Dérivation occasion dominante depuis agenda
3. Bucket météo
4. Construction d'une ligne de features par tenue du catalogue (incluant tailles + signaux de matching)
5. predict_proba sur chaque ligne
6. Tri descendant des scores
7. Retour top_k avec raisons explicatives + contexte résolu

Raisons explicatives (rules simples):

- correspond aux preferences de style
- adapte a la météo
- cohérent avec l'agenda
- bonne compatibilité globale

## 9. Paramètres fonctionnels importants

### 9.1 Paramètres d'entraînement

- --samples: taille du dataset synthétique
- --catalog: chemin catalogue tenues
- --output: chemin modèle joblib
- --metrics-output: chemin métriques JSON
- --model-candidates: liste modèles à comparer

### 9.2 Paramètres d'inférence

Endpoint /recommend:

- user_id
- gender
- age
- height_cm
- style_preferences
- body_shape (optionnel)
- body_measurements (optionnel)
- agenda
- location
- weather.temperature_c
- weather.condition
- top_k

Endpoint /recommend/auto:

- user_id
- location (optionnelle si présente dans profil)
- overrides optionnels: gender, age, height_cm, clothing_size, top_size, bottom_size, shoe_size,
  style_preferences, body_shape, body_measurements, agenda
- top_k

Endpoint /mirror/recommend-from-camera:

- image_base64
- location (optionnelle)
- threshold (identification faciale)
- top_k

Les endpoints de recommandation renvoient aussi `resolved_context`:

- source (manual/context/auto)
- location et weather effectivement utilises
- agenda_labels interpretes
- details OpenWeather resolves pour context/auto

## 10. Mapping metier internes

### 10.1 Morphologie (features.py)

Règles basées sur ratios épaules/hanches et taille/hanches:

- hourglass
- pear
- inverted_triangle
- oval
- rectangle
- unknown (si donnees absentes)

### 10.2 Météo

weather.condition + temperature_c -> bucket:

- rainy si condition pluie
- cold si temperature < 10
- hot si temperature > 24
- mild sinon

### 10.3 Agenda -> occasion dominante

Mots-clés detectés vers:

- work
- sport
- date
- event
- outdoor
- casual (fallback)

## 11. Performance et tuning

Actions recommandées pour améliorer le modèle:

1. Remplacer le dataset synthétique par interactions réelles

- feedback explicite: like/dislike
- feedback implicite: clic, durée de visualisation, tenue effectivement portée

2. Ajouter de nouvelles features

- saison
- pluie probable sur plage horaire
- formalité précise des évènements agenda
- contraintes vestimentaires dans les entreprises
- historique personnel de satisfaction

3. Tuner les hyperparamètres

- recherche sur n_estimators, max_depth, min_samples_leaf
- calibrage probabiliste (Platt/Isotonic)

4. Evaluation offline plus robuste

- validation croisée temporelle si données datées
- métriques top-k ranking (Precision@k, Recall@k, NDCG)

5. Monitoring production

- drift des distributions
- performance par segment (age, style, meteo)
- taux de non-reconnaissance camera

## 12. Limites actuelles

- Données d'entraînement synthétiques
- Heuristiques morphologie simplifiées
- Explications basées sur règles, pas SHAP/LIME
- Pas de re-entraînement online automatique
- Pas de boucle de feedback deja activée

## 13. Roadmap recommandee

1. Version 1 (actuelle)

- pipeline operationnel complet
- intégration camera + recommandation

2. Version 2

- collecte feedback utilisateur
- recalibration des scores
- ségmentation des modèles par contexte

3. Version 3

- personnalisation avancee
- apprentissage continu
- governance ML complète (monitoring, A/B tests, rollback)

## 14. Fichiers de reference

- src/outfit_ml/train.py
- src/outfit_ml/data.py
- src/outfit_ml/features.py
- src/outfit_ml/recommend.py
- src/outfit_ml/context.py
- src/outfit_ml/api.py
- models/outfit_ranker_metrics.json
- docs/quickstart.md
- docs/flutter_android_integration.md

## 15. Commandes utiles

**Entraînement:**

`python -m src.outfit_ml.train --samples 4000`

**Compilation de vérification:**

`~/.pyenv/bin/python -m compileall src` 

**Lancement API:**

`uvicorn src.outfit_ml.api:app --reload`

## 16. Pipeline feedback reel

**Collecte des interactions:**

- `POST /feedback/event` pour loguer impression/click/selected/dismissed
- `GET /feedback/stats` pour verifier le volume et la repartition

**Format de stockage:**

- JSON Lines dans `data/feedback/events.jsonl` (configurable via `FEEDBACK_LOG_PATH`)

**Transformation en dataset d'entraînement:**

- Groupe par `session_id`
- Positif: `selected` (et `click`)
- Negatif: tenues en `impression` non selectionnees
- Recalcule des features de matching depuis le catalogue

**Activation entraînement réel:**

`python -m src.outfit_ml.train --prefer-real-data --real-feedback-log data/feedback/events.jsonl --split-mode time`

**Fallback:**

- si volume reel insuffisant (< `--min-real-samples`) ou classes non exploitables, fallback automatique sur synthetique
