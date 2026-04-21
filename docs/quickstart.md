# Quick Start (Complet)

Cette version couvre le flux complet avec:

- recommandations manual/context/auto
- contexte meteo enrichi (`resolved_context`)
- prise en compte des tailles et overrides utilisateur en mode auto

## 1. Installer et entrainer

```bash
~/.pyenv/bin/python -m pip install -r requirements.txt
~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000
~/.pyenv/bin/python -m pip install face-recognition
```

## 2. Configurer l'environnement

```bash
cp .env.example .env
```

Valeurs minimales dans `.env` (mode local sans API backend):

```env
OPENWEATHER_API_KEY=ta_cle_openweather

MAGICMIRROR_DATA_SOURCE=file
MAGICMIRROR_PROFILE_FILE_TEMPLATE=data/users/{user_id}/profile.json
MAGICMIRROR_AGENDA_FILE_TEMPLATE=data/users/{user_id}/agenda_today.json

FACE_REGISTRY_PATH=data/vision/face_registry.json
```

## 3. Lancer l'API

```bash
uvicorn src.outfit_ml.api:app --reload
```

Interface de test rapide:

- `http://127.0.0.1:8000/ui`
- En mode auto, les champs meteo manuels sont masques et les details OpenWeather sont affiches dans les resultats.

## 4. Enroler un utilisateur (visage)

Appel `POST /vision/enroll` avec un visage net:

```json
{
  "user_id": "u-001",
  "image_base64": "data:image/jpeg;base64,..."
}
```

## 5. Tester le flux complet miroir intelligent

Appel unique `POST /mirror/recommend-from-camera`:

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "location": "Lyon",
  "threshold": 0.45,
  "top_k": 3
}
```

Retour attendu:

- utilisateur reconnu (`matched_user_id`)
- score visage (`face_match`)
- recommandations (`recommendation.suggestions`)

## 5 bis. Tester le mode auto avec overrides

Appel `POST /recommend/auto` (les champs fournis ecrasent les valeurs du profil):

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

Verifier dans la reponse:

- `resolved_context.source = "auto"`
- `resolved_context.agenda_labels` present
- `resolved_context.openweather` present (ville, ressenti, humidite, vent)

## 6. Integration Flutter Android

- Utiliser `camera` pour capturer une image.
- Encoder en base64 (`data:image/jpeg;base64,...`).
- Envoyer vers `/mirror/recommend-from-camera`.
- Sur emulation Android: backend `http://10.0.2.2:8000`.

Pour le guide complet Flutter, voir `docs/flutter_android_integration.md`.

## Depannage rapide

- `501` sur vision: installer `face-recognition`.
- `404` sur endpoint camera: utilisateur non reconnu, refaire enrollement.
- `502` meteo: verifier `OPENWEATHER_API_KEY`.
- `400` image: verifier format base64 et qu'un seul visage est visible.
- recommandations incoherentes en mode auto: verifier les overrides envoyes (`gender`, `age`, `top_size`, `bottom_size`, `shoe_size`, `agenda`).
