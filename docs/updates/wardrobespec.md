# mlOutfitSuggestion — Garde-robe individuelle & Moteur de composition

> Spec de la migration : liste fixe de tenues → items individuels + composition dynamique.

---

## Table des matières

1. [Schéma d'un item de garde-robe](#1-schéma-dun-item-de-garde-robe)
2. [Valeurs autorisées](#2-valeurs-autorisées)
3. [Saisie manuelle + image](#3-saisie-manuelle--image)
4. [Moteur de composition](#4-moteur-de-composition)
5. [Rôle du RAG dans la composition](#5-rôle-du-rag-dans-la-composition)
6. [Diversité & anti-répétition](#6-diversité--anti-répétition)
7. [Endpoints API](#7-endpoints-api)
8. [Migration depuis la liste fixe actuelle](#8-migration-depuis-la-liste-fixe-actuelle)
9. [Roadmap — phase suivante](#9-roadmap--phase-suivante)

---

## 1. Schéma d'un item de garde-robe

```json
{
  "item_id": "itm_8f3a1c",
  "user_id": "u-001",
  "category": "top",
  "subcategory": "chemise",
  "color_primary": "bleu_marine",
  "color_secondary": null,
  "material": "coton",
  "pattern": "uni",
  "formality_level": 3,
  "warmth_rating": 2,
  "season_suitability": ["printemps", "automne"],
  "occasion_tags": ["travail", "reunion"],
  "image_url": null,
  "auto_tagged": false,
  "is_favorite": false,
  "created_at": "2026-09-13T10:00:00Z",
  "last_suggested_at": null,
  "last_worn_at": null
}
```

### Champs obligatoires

| Champ | Type | Description |
|---|---|---|
| `category` | enum | Catégorie principale de l'item |
| `subcategory` | enum | Sous-type précis dans la catégorie |
| `color_primary` | enum | Couleur dominante |
| `formality_level` | int (1–5) | Niveau de formalité de l'item |
| `warmth_rating` | int (1–5) | Chaleur/isolation de l'item |

### Champs optionnels

| Champ | Type | Description |
|---|---|---|
| `color_secondary` | enum | Couleur secondaire (motif, détail) |
| `material` | enum | Matière dominante |
| `pattern` | enum | Motif (uni, rayé, imprimé...) |
| `season_suitability` | liste d'enum | Saisons adaptées |
| `occasion_tags` | liste libre | Tags d'occasion additionnels précisés par l'utilisateur |
| `image_url` | string | Image de l'item (upload) |

### Champs auto-générés (non saisis par l'utilisateur)

| Champ | Type | Description |
|---|---|---|
| `item_id` | string | Identifiant unique |
| `auto_tagged` | bool | `false` tant qu'il n'y a pas de tagging par vision — réservé pour plus tard |
| `is_favorite` | bool | `false` par défaut, modifiable via `PATCH` |
| `created_at` | datetime | Horodatage de création |
| `last_suggested_at` | datetime \| null | Dernière fois où l'item est apparu dans une suggestion |
| `last_worn_at` | datetime \| null | Dernière fois marquée "portée" (si feedback implémenté) |

---

## 2. Valeurs autorisées

### `category` / `subcategory`

| `category` | `subcategory` (exemples) |
|---|---|
| `top` | t_shirt, chemise, pull, sweat, debardeur |
| `bottom` | jean, pantalon, jupe, short, legging |
| `outerwear` | veste, manteau, blazer, doudoune, trench |
| `dress` | robe_casual, robe_soiree, combinaison |
| `shoes` | baskets, mocassins, bottines, sandales, chaussures_habillees |
| `accessory` | ceinture, echarpe, bonnet, sac, bijou |

### `color_primary` / `color_secondary`

`noir` · `blanc` · `gris` · `bleu_marine` · `bleu_clair` · `beige` · `marron` · `vert` · `rouge` · `rose` · `jaune` · `orange` · `violet` · `multicolore`

### `material`

`coton` · `laine` · `lin` · `soie` · `denim` · `cuir` · `synthétique` · `maille`

### `pattern`

`uni` · `rayé` · `imprimé` · `carreaux` · `à_pois`

### `season_suitability`

`printemps` · `été` · `automne` · `hiver` (liste, un item peut couvrir plusieurs saisons)

### `formality_level` (échelle commune à tous les items)

| Valeur | Sens |
|---|---|
| 1 | Très décontracté (sport, maison) |
| 2 | Décontracté (weekend, casual) |
| 3 | Smart casual (bureau non-formel) |
| 4 | Formel (réunion client, entretien) |
| 5 | Très formel (soirée, cérémonie) |

### `warmth_rating`

| Valeur | Sens |
|---|---|
| 1 | Très léger (été chaud) |
| 2 | Léger |
| 3 | Modéré (mi-saison) |
| 4 | Chaud |
| 5 | Très chaud (grand froid) |

---

## 3. Saisie manuelle + image

- Formulaire d'ajout rapide : seuls les champs obligatoires sont demandés par défaut (~30 sec/item), les optionnels sont repliés dans une section "détails" facultative.
- L'image est un champ indépendant, uploadée séparément (`multipart/form-data` ou `image_base64`), stockée via `image_url`.
- L'image ne déclenche **aucun tagging automatique pour l'instant** — elle sert uniquement à l'affichage dans l'UI (reconnaissance visuelle par l'utilisateur plutôt que via un nom générique).
- Le flag `auto_tagged: false` est posé dès la création, pour que l'ajout futur d'un tagger vision (pré-remplissage `color_primary`/`pattern`/`category` depuis l'image) n'exige aucun changement de schéma — seulement un changement de valeur du flag et un enrichissement des champs déjà existants.

---

## 4. Moteur de composition

Remplace le ranker actuel (qui scorait une liste fixe de tenues) par un pipeline en 4 étapes, exécuté sur les items individuels de l'utilisateur.

### Étape 1 — Filtres durs (déterministes)

Éliminent tout ce qui est incohérent avant scoring :

- `warmth_rating` de l'ensemble compatible avec `weather_bucket` du contexte résolu
- `formality_level` cohérent avec `dominant_occasion` (agenda du jour)
- `season_suitability` compatible avec la saison courante

### Étape 2 — Règles de compatibilité (style)

Sur les combinaisons survivantes :

- **Cohérence de formalité** : écart maximal toléré entre `formality_level` des pièces d'une même tenue (ex: écart ≤ 1)
- **Harmonie des couleurs** : règles de compatibilité entre `color_primary`/`color_secondary` des pièces (complémentaires, analogues, neutres passe-partout)
- **Cohérence matière/motif** : éviter les combinaisons de motifs incompatibles (ex: deux imprimés forts ensemble)

→ Ces règles sont alimentées par le corpus RAG (voir section 5) plutôt que codées en dur, pour rester ajustables sans redéploiement.

### Étape 3 — Scoring ML

Le ranker existant est réentraîné pour scorer des **combinaisons générées** (features agrégées des items + contexte + préférences utilisateur), et non plus une liste fixe de tenues prédéfinies.

### Étape 4 — Re-ranking diversité

Voir section 6.

---

## 5. Rôle du RAG dans la composition

Corpus de règles de style organisé par catégorie (même approche que mAIntenanceAssistance) :

```
data/corpus_style/
├── harmonie_couleurs.md
├── codes_occasion.md
├── matiere_meteo.md
└── morphologie.md
```

Le moteur interroge ce corpus avec le contexte résolu (`weather_bucket`, `dominant_occasion`, `agenda_labels`) pour :

1. Valider/justifier les combinaisons générées à l'étape 2
2. Fournir la matière première du champ `reasons` en langage naturel
3. Élargir dynamiquement le pool de combinaisons candidates plutôt que de se limiter aux seules règles codées en dur

---

## 6. Diversité & anti-répétition

Parmi les combinaisons bien scorées à l'étape 3, un re-ranking type **MMR** (maximal marginal relevance) pénalise la similarité avec :

- les tenues suggérées récemment (`last_suggested_at` proche dans le temps)
- les items déjà beaucoup utilisés dans les suggestions passées

`last_suggested_at` est mis à jour à chaque fois qu'un item apparaît dans une tenue proposée — indépendamment du fait qu'elle soit choisie ou non, pour garantir un vrai roulement.

---

## 7. Endpoints API

```
POST   /wardrobe/items          — créer un item (+ image optionnelle)
GET    /wardrobe/items          — lister la garde-robe d'un user_id
PATCH  /wardrobe/items/{id}     — éditer un item (ex: marquer favori, corriger une couleur)
DELETE /wardrobe/items/{id}     — retirer un item (usé, perdu, plus porté)
```

Les endpoints `/recommend`, `/recommend/context`, `/recommend/auto` existants conservent leur contrat de réponse, mais consomment désormais la garde-robe individuelle de l'utilisateur au lieu de la liste fixe de tenues.

---

## 8. Migration depuis la liste fixe actuelle

1. Décomposer chaque tenue prédéfinie existante en items individuels (dédupliquer les pièces communes entre tenues)
2. Renseigner les champs obligatoires (`category`, `subcategory`, `color_primary`, `formality_level`, `warmth_rating`) pour chaque item extrait
3. Faire tourner en parallèle l'ancien ranker (sur liste fixe) et le nouveau moteur de composition, le temps de valider la qualité des combinaisons générées avant bascule complète

---

## 9. Roadmap — phase suivante

Une fois la garde-robe individuelle et le moteur de composition stabilisés : questionnaire de préférences (initial à l'onboarding + micro-questionnaires ponctuels), pour enrichir `style_preferences` au-delà des tags actuels et capter du feedback explicite en complément des événements `/feedback/*` déjà existants.