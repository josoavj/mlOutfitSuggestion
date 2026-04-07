# Documentation Complete du Modele ML

## 1. But du modele

Le modele predit la pertinence d'une tenue pour un utilisateur dans un contexte donne.

Le contexte combine:
- profil utilisateur (sexe, age, taille, preferences, morphologie)
- contexte journee (agenda)
- contexte externe (meteo)
- metadonnees de la tenue (style, occasion, compatibilite)

Sortie principale:
- un score de compatibilite par tenue
- un classement top-k des tenues recommandees

## 2. Architecture globale

La solution comporte deux couches:

1. Couche contextuelle
- normalisation agenda -> occasion dominante
- conversion meteo brute -> bucket meteo
- inference de morphologie a partir de mensurations

2. Couche ML de ranking
- modele de classification binaire (pipeline scikit-learn)
- evaluation de la proba positive par tenue
- tri descendant des probabilites

Fichiers clefs:
- src/outfit_ml/features.py
- src/outfit_ml/data.py
- src/outfit_ml/train.py
- src/outfit_ml/recommend.py

## 3. Donnees d'entrainement

Le dataset d'entrainement est synthetique (bootstrapping), genere dans src/outfit_ml/data.py.

### 3.1 Variables simulees

- age: entier [16, 65]
- height_cm: entier [150, 200]
- gender: female | male | non_binary
- body_shape: hourglass | rectangle | pear | inverted_triangle | oval
- occasion: work | meeting | casual | sport | event | date | outdoor
- weather: cold | mild | hot | rainy
- style preferences: 1 a 2 styles parmi:
  - classic, minimalist, casual, sport, elegant, practical
- tenue cible: echantillonnee depuis le catalogue configs/outfit_catalog.json

### 3.2 Construction du label

La cible binaire label est derivee d'un signal pondere:

signal = 0.35 * style_match
       + 0.25 * occasion_match
       + 0.20 * weather_match
       + 0.10 * shape_match
       + 0.10 * gender_match

Puis:
- noisy_threshold = 0.55 +/- bruit uniforme dans [-0.08, +0.08]
- label = 1 si signal >= noisy_threshold, sinon 0

Ce schema donne un jeu exploitable rapidement, mais ne remplace pas des donnees reelles de production.

## 4. Features du modele

Les features sont definies dans src/outfit_ml/train.py.

### 4.1 Features categorielles

- gender
- body_shape
- occasion
- weather
- outfit_id

Encodage:
- OneHotEncoder(handle_unknown="ignore")

### 4.2 Features numeriques

- age
- height_cm
- style_match
- occasion_match
- weather_match
- shape_match
- gender_match
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

## 5. Modeles candidats et hyperparametres

Selection automatique du meilleur modele selon ROC-AUC sur split validation.

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

## 6. Pipeline d'entrainement

Implementation: src/outfit_ml/train.py

Etapes:
1. Chargement catalogue tenues
2. Generation dataset synthetique
3. Split train/test stratifie (80/20)
4. Entrainement des modeles candidats
5. Evaluation metriques
6. Selection du meilleur selon ROC-AUC
7. Sauvegarde du pipeline et metriques

Commande standard:

python -m src.outfit_ml.train --samples 4000

Fichiers produits:
- models/outfit_ranker.joblib
- models/outfit_ranker_metrics.json

## 7. Metriques et interpretation

Metriques calculees:
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

Interpretation rapide:
- ROC-AUC et AP eleves: bonne separation sur donnees synthetiques
- recall > precision: le modele favorise la recuperation des tenues pertinentes

## 8. Inference et ranking

Implementation: src/outfit_ml/recommend.py

Etapes runtime:
1. Inference morphologie si non fournie
2. Derivation occasion dominante depuis agenda
3. Bucket meteo
4. Construction d'une ligne de features par tenue du catalogue
5. predict_proba sur chaque ligne
6. Tri descendant des scores
7. Retour top_k avec raisons explicatives

Raisons explicatives (rules simples):
- correspond aux preferences de style
- adapte a la meteo
- coherent avec l'agenda
- bonne compatibilite globale

## 9. Parametres fonctionnels importants

### 9.1 Parametres d'entrainement

- --samples: taille du dataset synthetique
- --catalog: chemin catalogue tenues
- --output: chemin modele joblib
- --metrics-output: chemin metriques JSON
- --model-candidates: liste modeles a comparer

### 9.2 Parametres d'inference

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
- location (optionnelle si presente profil)
- top_k

Endpoint /mirror/recommend-from-camera:
- image_base64
- location (optionnelle)
- threshold (identification faciale)
- top_k

## 10. Mapping metier internes

### 10.1 Morphologie (features.py)

Regles basees sur ratios epaules/hanches et taille/hanches:
- hourglass
- pear
- inverted_triangle
- oval
- rectangle
- unknown (si donnees absentes)

### 10.2 Meteo

weather.condition + temperature_c -> bucket:
- rainy si condition pluie
- cold si temperature < 10
- hot si temperature > 24
- mild sinon

### 10.3 Agenda -> occasion dominante

Mots-cles detectes vers:
- work
- sport
- date
- event
- outdoor
- casual (fallback)

## 11. Performance et tuning

Actions recommandees pour ameliorer le modele:

1. Remplacer le dataset synthetique par interactions reelles
- feedback explicite: like/dislike
- feedback implicite: clic, duree de visualisation, tenue effectivement portee

2. Ajouter de nouvelles features
- saison
- pluie probable sur plage horaire
- formalite precise des evenements agenda
- contraintes vestimentaires entreprise
- historique personnel de satisfaction

3. Tuner les hyperparametres
- recherche sur n_estimators, max_depth, min_samples_leaf
- calibrage probabiliste (Platt/Isotonic)

4. Evaluation offline plus robuste
- validation croisee temporelle si donnees datees
- metriques top-k ranking (Precision@k, Recall@k, NDCG)

5. Monitoring production
- drift des distributions
- performance par segment (age, style, meteo)
- taux de non-reconnaissance camera

## 12. Limites actuelles

- Donnees d'entrainement synthetiques
- Heuristiques morphologie simplifiees
- Explications basees sur regles, pas SHAP/LIME
- Pas de re-entrainement online automatique
- Pas de boucle de feedback deja activee

## 13. Roadmap recommandee

1. Version 1 (actuelle)
- pipeline operationnel complet
- integration camera + recommandation

2. Version 2
- collecte feedback utilisateur
- recalibration des scores
- segmentation des modeles par contexte

3. Version 3
- personnalisation avancee
- apprentissage continu
- governance ML complete (monitoring, A/B tests, rollback)

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

Entrainement:

python -m src.outfit_ml.train --samples 4000

Compilation de verification:

~/.pyenv/bin/python -m compileall src

Lancement API:

uvicorn src.outfit_ml.api:app --reload
