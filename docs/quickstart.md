# Quick Start — Guide complet

> Ce guide couvre le flux complet avec recommandations `manual` / `context` / `auto`, contexte météo enrichi (`resolved_context`) et prise en compte des tailles et overrides utilisateur en mode auto.

---

## Table des matières

1. [Installer et entraîner](#1-installer-et-entraîner)
2. [Configurer l'environnement](#2-configurer-lenvironnement)
3. [Lancer l'API](#3-lancer-lapi)
4. [Enrôler un utilisateur](#4-enrôler-un-utilisateur-visage)
5. [Tester le flux miroir intelligent](#5-tester-le-flux-complet-miroir-intelligent)
6. [Tester le mode auto avec overrides](#5-bis-tester-le-mode-auto-avec-overrides)
7. [Intégration Flutter Android](#6-intégration-flutter-android)
8. [Dépannage rapide](#dépannage-rapide)

---

## 1. Installer et entraîner

```bash
~/.pyenv/bin/python -m pip install -r requirements.txt
~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000
~/.pyenv/bin/python -m pip install face-recognition
```

---

## 2. Configurer l'environnement

```bash
cp .env.example .env
```

Valeurs minimales dans `.env` pour un fonctionnement **local sans API backend** :

```env
OPENWEATHER_API_KEY=ta_cle_openweather
MAGICMIRROR_DATA_SOURCE=file
MAGICMIRROR_PROFILE_FILE_TEMPLATE=data/users/{user_id}/profile.json
MAGICMIRROR_AGENDA_FILE_TEMPLATE=data/users/{user_id}/agenda_today.json
FACE_REGISTRY_PATH=data/vision/face_registry.json
```

---

## 3. Lancer l'API

```bash
uvicorn src.outfit_ml.api:app --reload
```

Interface de test rapide : `http://127.0.0.1:8000/ui`

> En mode auto, les champs météo manuels sont masqués et les détails OpenWeather sont affichés dans les résultats.

---

## 4. Enrôler un utilisateur (visage)

**`POST /vision/enroll`** — fournir un visage net :

```json
{
  "user_id": "u-001",
  "image_base64": "data:image/jpeg;base64,..."
}
```

---

## 5. Tester le flux complet miroir intelligent

**`POST /mirror/recommend-from-camera`**

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "location": "Lyon",
  "threshold": 0.45,
  "top_k": 3
}
```

**Retour attendu :**

| Champ | Description |
|---|---|
| `matched_user_id` | Utilisateur reconnu |
| `face_match` | Score de correspondance visage |
| `recommendation.suggestions` | Liste des tenues recommandées |

---

## 5 bis. Tester le mode auto avec overrides

**`POST /recommend/auto`** — les champs fournis écrasent les valeurs du profil :

```json
{
  "user_id": "u-001",
  "location": "Lyon",
  "gender": "female",
  "age": 29,
  "top_size": "m",
  "bottom_size": "m",
  "shoe_size": "40",
  "style_preferences": ["minimalist", "elegant"],
  "agenda": ["work", "meeting"],
  "top_k": 3
}
```

**Vérifier dans la réponse :**

| Champ | Valeur attendue |
|---|---|
| `resolved_context.source` | `"auto"` |
| `resolved_context.agenda_labels` | Présent |
| `resolved_context.openweather` | Présent (ville, ressenti, humidité, vent) |

---

## 6. Intégration Flutter Android

1. Utiliser le package `camera` pour capturer une image.
2. Encoder en base64 (`data:image/jpeg;base64,...`).
3. Envoyer vers `POST /mirror/recommend-from-camera`.
4. Sur émulateur Android, utiliser l'adresse backend : `http://10.0.2.2:8000`.

Pour le guide complet, voir [`docs/flutter_android_integration.md`](docs/flutter_android_integration.md).

---

## Dépannage rapide

| Erreur | Cause probable | Solution |
|---|---|---|
| `501` sur vision | `face-recognition` absent | `pip install face-recognition` |
| `404` sur endpoint caméra | Utilisateur non reconnu | Refaire l'enrôlement |
| `502` météo | Clé API invalide ou absente | Vérifier `OPENWEATHER_API_KEY` |
| `400` image | Format incorrect ou plusieurs visages | Vérifier le format base64 et qu'un seul visage est visible |
| Recommandations incohérentes (mode auto) | Overrides incorrects | Vérifier `gender`, `age`, `top_size`, `bottom_size`, `shoe_size`, `agenda` |