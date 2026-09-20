# Ontologie OWL — mlOutfitSuggestion

## Pourquoi une ontologie formelle ici

Aujourd'hui, la connaissance du domaine (quelles couleurs vont ensemble,
quelle formalité pour quelle occasion, quelles catégories sont mutuellement
exclusives) est **dispersée et dupliquée** :

- `composition/compatibility.py` — `NEUTRALS`, `COMPLEMENTARY_PAIRS` codés en dur
- `composition/rag.py` — les mêmes règles, réécrites en prose dans
  `data/corpus_style/*.md`, interrogées par recherche "sémantique" (une
  approximation par embeddings, pas un vrai raisonnement)
- `recommend.py` — `formality_map`/`warmth_map` codés en dur pour les occasions
- `wardrobe/models.py` — les catégories sont un simple enum, sans hiérarchie
  ni contrainte : rien n'empêche formellement qu'un item soit mal catégorisé

Une ontologie OWL centralise tout ça en **une seule source de vérité**,
versionnée, et permet un vrai raisonnement logique (classification
automatique, cohérence, inférence) plutôt que des règles éparpillées et
recopiées à la main à plusieurs endroits — ce qui est justement ce qui a
produit le bug de l'audit précédent (`formality_level` vs `formality_levels`
désynchronisés entre deux fichiers).

## Ce que l'ontologie modélise

**Classes** : `Garment` (avec sous-classes disjointes `Top`, `Bottom`,
`Outerwear`, `Dress`, `Shoes`, `Accessory`, elles-mêmes spécialisées —
`Shirt`, `Jean`, `Sneakers`...), `Outfit`, `Color`, `Material`, `Pattern`,
`Season`, `Occasion` (avec sous-classes `Work`, `Meeting`, `Event`...),
`StyleTag`, `BodyShape`.

**Propriétés objet** : `hasPrimaryColor`, `hasMaterial`, `hasPattern`,
`suitableForSeason`, `suitableForBodyShape`, `hasStyle`, `hasPart`
(Outfit → Garment), `harmonizesWith` (symétrique, entre couleurs),
`colorCompatibleWith` (symétrique, entre garments — **inférée**, jamais assertée).

**Propriétés de données** : `formalityLevel`, `warmthLevel` (non
fonctionnelles — listes, comme `formality_levels`/`warmth_ratings` côté
Pydantic), `requiresMinFormality` (sur Occasion).

**Classes définies (classification automatique par le raisonneur)** :
`CasualGarment` / `FormalGarment` (selon `formalityLevel`),
`WarmGarment` / `LightGarment` (selon `warmthLevel`),
`FormalOutfit` / `CasualOutfit` (selon les garments qui composent l'outfit).
Un garment n'est **jamais taggé manuellement** comme formel ou casual — le
raisonneur le déduit de ses valeurs de `formalityLevel`, comme démontré par
le test ci-dessous.

**Règle SWRL** : compatibilité couleur entre deux pièces distinctes, dérivée
de `harmonizesWith` :

```
Garment(?g1), Garment(?g2), hasPrimaryColor(?g1, ?c1),
hasPrimaryColor(?g2, ?c2), harmonizesWith(?c1, ?c2), DifferentFrom(?g1, ?g2)
-> colorCompatibleWith(?g1, ?g2)
```

## Démonstration (exécutée, pas hypothétique)

Avec 4 pièces de test (chemise bleu marine formalité 3-4, pantalon rouge
formalité 4, t-shirt orange formalité 1, jean gris formalité 2), le
raisonneur HermiT :

- classe automatiquement la chemise et le pantalon en `FormalGarment`
  (aucune des deux n'a été taguée "formelle" à la main — c'est déduit de
  `formalityLevel`)
- classe le t-shirt et le jean en `CasualGarment`/`LightGarment`
- infère `colorCompatibleWith` entre chemise↔pantalon (bleu marine/rouge,
  paire complémentaire) et chemise↔jean, jean↔t-shirt (gris = neutre)
- **n'infère PAS** de compatibilité entre le t-shirt orange et le pantalon
  rouge (orange/rouge non déclarés harmonieux) — preuve que ce n'est pas
  juste "tout est compatible avec tout"

## ⚠️ Piège rencontré et corrigé : l'hypothèse du monde ouvert

Première tentative : la règle SWRL ne s'est déclenchée pour **aucune** paire
de couleurs testée en dehors du jeu de démo initial. Cause : en OWL, deux
individus nommés distincts ne sont **pas** supposés différents l'un de
l'autre par défaut (contrairement à la plupart des langages de
programmation) — `DifferentFrom(?g1, ?g2)` dans la règle ne se déclenche
donc que si on déclare explicitement `AllDifferent(...)` sur le groupe
d'individus. Dans le premier test, ça marchait "par accident" parce que les
items de démo appartenaient à des classes deux-à-deux disjointes
(`Shirt`/`Trousers`/`TShirt`/`Jean`, sous `AllDisjoint`), ce qui suffit
aussi à prouver leur différence. Pour les items de garde-robe réels, chaque
catégorie (Top, Bottom, Shoes...) étant déjà disjointe, ce piège ne se
posera pas en pratique — mais bon à savoir si vous étendez l'ontologie.

## ⚠️ Ne PAS raisonner en direct dans l'API

Le raisonneur HermiT prend ~1.5 seconde sur cette ontologie pourtant petite
(démarrage JVM inclus). Totalement incompatible avec un endpoint
`/recommend` appelé à chaque affichage du miroir. **Le raisonnement se fait
une fois, offline** (`ontology/export_rules.py`), et exporte les résultats
utiles dans des JSON légers (`data/ontology_derived/*.json`) que l'app lit
au runtime sans dépendance à owlready2 ni à Java (`composition/ontology_rules.py`).

## Pipeline

```
ontology/outfit_ontology.py   → construit l'ontologie (classes, individus, règles)
         │
         ▼ (python -m ontology.export_rules)
ontology/export_rules.py      → lance HermiT UNE FOIS, exporte les inférences
         │
         ▼
data/ontology_derived/*.json  → lu au runtime, aucune dépendance lourde
         │
         ▼
composition/ontology_rules.py → interface simple (colors_harmonize, min_formality_for_occasion)
```

À régénérer (`python -m ontology.export_rules`) chaque fois que
`outfit_ontology.py` change — à automatiser en CI (déclenché sur modif de
ce fichier) plutôt qu'à faire à la main indéfiniment.

## Ce qui N'EST PAS fait

1. **Pas encore branché dans `compatibility.py`/`recommend.py`** —
   `composition/ontology_rules.py` est prêt à l'emploi (`colors_harmonize`,
   `min_formality_for_occasion`), mais je ne l'ai pas connecté pour ne pas
   mélanger ce chantier avec le bug bloquant de l'audit précédent
   (`formality_level` vs `formality_levels`). Une fois ce bug corrigé,
   brancher est un remplacement direct des dicts codés en dur.
2. **`Material`, `Pattern`, `Season`, `StyleTag`, `BodyShape`** ont des
   classes dans l'ontologie mais pas encore d'individus ni de règles
   d'inférence dessus — seuls `Color` et `Occasion` sont peuplés pour cette
   première version. Prochaine extension naturelle.
3. **Java requis dans l'image Docker** *seulement* pour régénérer les JSON
   (offline/CI) — **pas nécessaire dans l'image de production**, puisque
   `composition/ontology_rules.py` ne dépend que des JSON déjà générés.
4. **Migration de `data/corpus_style/*.md` (RAG)** — à terme, ce corpus
   pourrait être généré depuis l'ontologie plutôt que maintenu à la main en
   parallèle, pour éviter une nouvelle désynchronisation entre les deux.
   Pas fait ici.

## Fichiers livrés

```
ontology/outfit_ontology.py    — construction de l'ontologie
ontology/export_rules.py       — raisonnement offline + export JSON
ontology/evaluate.py           — métriques, cohérence, questions de compétence
ontology/visualize.py          — génère les 2 graphes (hiérarchie + harmonie couleurs)
ontology/outfit_ontology.owl   — fichier ontologie généré (RDF/XML)
data/ontology_derived/*.json   — résultats pré-calculés
composition/ontology_rules.py  — interface runtime légère
docs/qualite_evaluation.md     — métriques, cohérence, questions de compétence, pitfalls
docs/graph_class_hierarchy.svg — hiérarchie de classes (généré, pas dessiné à la main)
docs/graph_color_harmony.png   — réseau des couleurs et leurs harmonies
```

Voir `docs/qualite_evaluation.md` pour l'évaluation complète (cohérence
logique, questions de compétence, analyse des pièges de modélisation
courants). Reproductible avec `python -m ontology.evaluate` et
`python -m ontology.visualize`.

Dépendance à ajouter : `owlready2` dans `requirements.txt` (uniquement
nécessaire pour construire/régénérer l'ontologie, pas pour la servir), et
`graphviz`/`networkx`/`matplotlib` en dépendances de dev uniquement (pour
`visualize.py`).
