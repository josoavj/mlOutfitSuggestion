# mlOutfitSuggestion — Questionnaire de préférences

> Spec de la phase 2 : enrichir `style_preferences` via un questionnaire initial + micro-questionnaires ponctuels.

---

## Table des matières

1. [Deux formats, deux objectifs](#1-deux-formats-deux-objectifs)
2. [Schéma des préférences utilisateur](#2-schéma-des-préférences-utilisateur)
3. [Questionnaire initial (onboarding)](#3-questionnaire-initial-onboarding)
4. [Micro-questionnaires ponctuels](#4-micro-questionnaires-ponctuels)
5. [Logique de déclenchement des micro-questionnaires](#5-logique-de-déclenchement-des-micro-questionnaires)
6. [Intégration avec le moteur de composition](#6-intégration-avec-le-moteur-de-composition)
7. [Endpoints API](#7-endpoints-api)
8. [Articulation avec le feedback implicite existant](#8-articulation-avec-le-feedback-implicite-existant)

---

## 1. Deux formats, deux objectifs

| Format | Quand | Objectif |
|---|---|---|
| **Questionnaire initial** | Une fois, à la création du profil | Poser une base de préférences solide avant toute suggestion |
| **Micro-questionnaire** | Ponctuellement, pas à chaque passage | Affiner/faire évoluer le profil dans le temps, capter du feedback explicite ciblé |

---

## 2. Schéma des préférences utilisateur

```json
{
  "user_id": "u-001",
  "style_preferences": {
    "styles_aimes": ["minimalist", "elegant"],
    "styles_evites": ["streetwear"],
    "couleurs_aimees": ["bleu_marine", "beige"],
    "couleurs_evitees": ["orange"],
    "niveau_formalite_prefere": 3,
    "items_bannis": ["itm_8f3a1c"],
    "tolerance_meteo": "frileux"
  },
  "onboarding_completed_at": "2026-09-13T10:00:00Z",
  "last_micro_survey_at": null,
  "preferences_version": 1
}
```

| Champ | Type | Description |
|---|---|---|
| `styles_aimes` | liste enum | Styles à favoriser dans le scoring |
| `styles_evites` | liste enum | Styles à pénaliser/exclure |
| `couleurs_aimees` | liste enum | Couleurs à favoriser |
| `couleurs_evitees` | liste enum | Couleurs à pénaliser/exclure |
| `niveau_formalite_prefere` | int (1–5) | Biais de formalité par défaut (hors contrainte d'agenda) |
| `items_bannis` | liste d'`item_id` | Items à ne jamais proposer, même s'ils scorent bien |
| `tolerance_meteo` | enum (`frileux`, `neutre`, `resistant`) | Ajuste le `warmth_rating` cible par rapport à la météo brute |
| `preferences_version` | int | Incrémenté à chaque mise à jour, utile pour le suivi d'évolution du style |

---

## 3. Questionnaire initial (onboarding)

Déclenché une seule fois, avant la première suggestion. Objectif : rester court (< 2 minutes) — on affine ensuite via les micro-questionnaires, pas besoin d'être exhaustif dès le départ.

| # | Question | Type | Alimente |
|---|---|---|---|
| 1 | Quels styles te correspondent le mieux ? | choix multiple | `styles_aimes` |
| 2 | Y a-t-il des styles que tu ne veux jamais voir proposés ? | choix multiple | `styles_evites` |
| 3 | Quelles couleurs portes-tu le plus volontiers ? | choix multiple | `couleurs_aimees` |
| 4 | Des couleurs à éviter ? | choix multiple | `couleurs_evitees` |
| 5 | Es-tu plutôt à l'aise en tenue formelle ou tu préfères rester casual, même au travail ? | échelle 1–5 | `niveau_formalite_prefere` |
| 6 | Tu as plutôt tendance à avoir froid ou chaud par rapport aux autres ? | choix unique (`frileux`/`neutre`/`resistant`) | `tolerance_meteo` |

À la validation : `onboarding_completed_at` est posé, `preferences_version = 1`.

---

## 4. Micro-questionnaires ponctuels

Courts (1 à 2 questions max), ciblés sur un signal précis plutôt que de tout redemander.

### Exemples de micro-questionnaires

| Contexte de déclenchement | Question posée | Alimente |
|---|---|---|
| Un item a été suggéré plusieurs fois mais jamais choisi | "On dirait que [item] ne te convient pas trop — on arrête de te le proposer ?" | `items_bannis` |
| Une nouvelle saison démarre | "Ton style a changé depuis [saison précédente] ?" | `styles_aimes` / `styles_evites` |
| Plusieurs refus consécutifs sur un même niveau de formalité | "Tes tenues récentes te semblaient trop habillées ou pas assez ?" | `niveau_formalite_prefere` |
| X mois depuis la dernière mise à jour | "Toujours d'accord avec tes préférences de couleurs actuelles ?" | `couleurs_aimees` / `couleurs_evitees` |

---

## 5. Logique de déclenchement des micro-questionnaires

Pas à chaque passage (ça userait l'utilisateur) — déclenché par un signal, pas par le temps seul :

- **Basé sur le feedback implicite** : un pattern répété dans `/feedback/*` (ex: `dismissed` répété sur un même item ou un même `formality_level`) déclenche le micro-questionnaire correspondant
- **Basé sur un délai minimum** : jamais plus d'un micro-questionnaire toutes les X ouvertures de l'app, même si plusieurs signaux sont détectés en même temps (un seul à la fois, le plus pertinent)
- **Opt-out possible** : l'utilisateur peut ignorer un micro-questionnaire sans qu'il ne se redéclenche immédiatement pour le même signal

---

## 6. Intégration avec le moteur de composition

Les préférences interviennent à deux endroits du pipeline de composition (voir spec précédente) :

- **Étape 1 (filtres durs)** : `items_bannis` retire les items concernés avant même le scoring
- **Étape 3 (scoring ML)** : `styles_aimes`/`styles_evites`, `couleurs_aimees`/`couleurs_evitees`, `niveau_formalite_prefere` et `tolerance_meteo` entrent comme features de biais dans le score de la combinaison, en plus du contexte du jour

---

## 7. Endpoints API

```
GET    /preferences/{user_id}              — récupérer les préférences actuelles
PUT    /preferences/{user_id}               — mise à jour complète (ex: après onboarding)
PATCH  /preferences/{user_id}               — mise à jour partielle (ex: après un micro-questionnaire)
GET    /preferences/{user_id}/onboarding    — vérifier si l'onboarding a été complété
POST   /preferences/{user_id}/micro-survey  — soumettre la réponse à un micro-questionnaire déclenché
```

---

## 8. Articulation avec le feedback implicite existant

Le questionnaire capte du **feedback explicite** (l'utilisateur déclare une préférence), les endpoints `/feedback/*` existants captent du **feedback implicite** (clic, sélection, rejet). Les deux se complètent :

- Le feedback implicite **détecte** les signaux (ex: rejets répétés) et **déclenche** les micro-questionnaires pertinents (section 5)
- Le questionnaire **confirme et structure** ce que le feedback implicite ne fait que suggérer, avant de modifier durablement le profil (`items_bannis`, `styles_evites`...)

Cette boucle évite deux écueils : sur-réagir à un rejet isolé (bruit) ou attendre indéfiniment un volume de données suffisant pour inférer une préférence sans jamais la confirmer explicitement.