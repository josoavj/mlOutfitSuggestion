# Qualité et évaluation de l'ontologie

> Tous les chiffres et résultats ci-dessous proviennent de l'exécution réelle
> de `ontology/evaluate.py` sur la version actuelle de l'ontologie — pas
> d'estimation. Reproductible avec `python -m ontology.evaluate`.

---

## 1. Métriques structurelles

| Métrique | Valeur |
|---|---|
| Classes | 33 |
| Propriétés objet | 11 |
| Propriétés de données | 3 |
| Individus | 19 |
| Classes définies (`equivalent_to`, classification automatique) | 6 |
| Groupes de disjonction (`AllDisjoint`) | 2 |
| Règles SWRL | 1 |
| Profondeur max. de la hiérarchie de classes | 3 |

Une ontologie avec 6 classes *définies* sur 33 (≈18%) signifie qu'une part
non négligeable du raisonnement n'est pas juste de la classification
manuelle déguisée — le raisonneur fait un travail réel de classification
(`CasualGarment`, `FormalGarment`, `WarmGarment`, `LightGarment`,
`FormalOutfit`, `CasualOutfit`).

Ces métriques sont volontairement modestes — c'est une v0.1 couvrant
`Color` et `Occasion` en profondeur, avec les classes de `Material`,
`Pattern`, `Season`, `StyleTag`, `BodyShape` posées mais pas encore
peuplées (voir §4, limites connues).

## 2. Cohérence logique

Le test de cohérence standard en ingénierie ontologique : lancer le
raisonneur et vérifier qu'aucune classe ne se réduit à `owl:Nothing`
(insatisfiable — un signe qu'un ensemble d'axiomes se contredit).

```
Cohérente : True
Classes insatisfiables : []
```

Résultat propre. Attendu vu la taille modeste de l'ontologie, mais ça vaut
la peine de l'exécuter à chaque changement — une contradiction devient vite
non-évidente dès qu'on ajoute des classes définies et des règles SWRL qui
interagissent entre elles.

## 3. Questions de compétence (méthodologie Grüninger & Fox)

Principe : définir *avant* l'évaluation les questions auxquelles
l'ontologie doit savoir répondre, puis vérifier par une requête réelle —
pas en relisant les axiomes à l'œil.

| # | Question | Réponse obtenue | Résultat |
|---|---|---|---|
| CQ1 | Quelles couleurs s'harmonisent avec BleuMarine ? | Rouge, Noir, Beige, Blanc, Gris, Marron, BleuClair, Vert, Rose, Jaune, Orange, Violet, Multicolore (13, sans doublon) | ✅ PASS |
| CQ2 | Un item avec `formalityLevel=5` est-il classé `FormalGarment` **sans jamais avoir été tagué comme tel** ? | `True` (reclassé automatiquement par HermiT) | ✅ PASS |
| CQ3 | Quelle formalité minimale pour l'occasion `Meeting` ? | `4` | ✅ PASS |
| CQ4 | `Top` et `Bottom` sont-ils bien mutuellement exclusifs ? | `True` | ✅ PASS |

CQ2 est la plus significative des quatre : elle prouve que la
classification est un vrai calcul du raisonneur (subsomption via
`equivalent_to`), pas une relecture d'une valeur assertée à la main quelque
part.

## 4. Analyse des défauts courants (inspirée d'OOPS!)

Passage en revue des pièges classiques de modélisation OWL (checklist type
[OOPS! — OntOlogy Pitfall Scanner](http://oops.linkeddata.es/)) :

| Piège | Vérifié | Résultat |
|---|---|---|
| Classes non connectées (aucune propriété ne les référence) | ✅ | `Material`, `Pattern`, `Season`, `StyleTag`, `BodyShape` ont des propriétés définies (`hasMaterial`, etc.) mais **aucun individu ni assertion** pour l'instant — posées mais inertes. Pas un défaut de modélisation, une limite de couverture (§5). |
| Disjonction manquante entre sous-classes sœurs | ✅ corrigé | `Occasion` (Casual/Work/Meeting/Event/Sport) n'était **pas** déclaré disjoint dans la v0 — corrigé dans cette révision (`AllDisjoint` ajouté). |
| Cycles dans la hiérarchie de classes | ✅ | Aucun — vérifié par construction (`is_a` toujours vers le parent direct, jamais de retour). |
| Propriétés sans domaine/portée | ✅ | Toutes déclarées via la syntaxe `A >> B` d'owlready2, qui fixe domaine et portée automatiquement. |
| Propriétés sans inverse quand une relation en aurait besoin | ✅ corrigé | `hasPart`/`isPartOf` n'avait pas d'inverse dans la v0 — ajouté. |
| Classes/propriétés sans annotation (`rdfs:comment`) | ✅ corrigé | La v0 avait des `pass` sans docstring sur ~20 classes/propriétés — chacune a maintenant un commentaire en français (les docstrings Python deviennent `rdfs:comment` via owlready2). |
| Doublons dans les assertions de propriété | ✅ corrigé | `BleuMarine.harmonizesWith` contenait certaines couleurs en double dans la v0 (ex: `Rouge` apparaissait deux fois, listé à la fois comme neutre-adjacent et comme paire complémentaire explicite). Sans conséquence logique (OWL traite les propriétés comme des ensembles), mais nettoyé pour la lisibilité — construction par un `set` de paires avant assertion. |

## 5. Limites connues (honnêtes, pas cachées)

- **Couverture partielle** : seules `Color` et `Occasion` ont des individus
  et des règles d'inférence. `Material`, `Pattern`, `Season`, `StyleTag`,
  `BodyShape` existent comme classes/propriétés mais sont vides — la
  prochaine extension naturelle.
- **Une seule règle SWRL** (compatibilité couleur). D'autres candidates
  identifiées mais pas implémentées : formalité d'un garment vs formalité
  requise par une occasion (comparer `formalityLevel` à
  `requiresMinFormality` par une règle plutôt qu'en Python dans
  `filters.py`), cohérence matière/saison.
- **`isPartOf`/`hasPart` n'ont pas d'axiome de cardinalité** — rien
  n'empêche actuellement de déclarer un `Outfit` avec zéro pièce, ou 200.
  À restreindre si utile (ex: au moins 1 `Shoes`, au plus 1 `Outerwear`).
- **Expressivité** : profil approximatif OWL 2 DL, fragment ALCHQ(D) —
  intersections/unions de classes, restrictions existentielles (`some`) et
  universelles (`only`), restrictions de type de données avec bornes
  (`ConstrainedDatatype`), hiérarchie de propriétés implicite via les
  sous-classes de `Garment`. La règle SWRL ajoutée sort formellement du
  fragment OWL 2 DL pur — HermiT la traite en mode *DL-safe* (elle ne
  s'applique qu'aux individus explicitement nommés, jamais à des individus
  anonymes potentiels), ce qui garantit la décidabilité mais restreint un
  peu la portée théorique de l'inférence par rapport à une règle SWRL
  générale.

## 6. Graphes

- `graph_class_hierarchy.svg` — hiérarchie complète des classes, avec les
  classes définies en violet (celles que le raisonneur peuple tout seul) et
  les disjonctions en pointillés rouges. Dense (beaucoup d'arêtes de
  disjonction qui se croisent) — lisible en zoomant sur le SVG, une
  prochaine passe pourrait séparer visuellement le sous-graphe Garment du
  sous-graphe Occasion.
- `graph_color_harmony.png` — réseau des couleurs et leurs relations
  `harmonizesWith`. Les neutres (gris, au centre) sont connectés à tout ;
  les couleurs vives (bleu, en périphérie) ne sont reliées qu'à leurs
  paires complémentaires déclarées. C'est visuellement le graphe que la
  règle SWRL de compatibilité couleur parcourt réellement à l'exécution.

## Comment reproduire cette évaluation

```bash
python -m ontology.evaluate     # métriques + cohérence + questions de compétence
python -m ontology.visualize    # régénère les deux graphes
```

À relancer après toute modification de `ontology/outfit_ontology.py`, et à
intégrer en CI si l'ontologie devient amenée à évoluer souvent (un test qui
échoue sur `consistent=False` ou sur une question de compétence en échec
bloque le merge).
