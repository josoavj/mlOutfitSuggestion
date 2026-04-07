# Quick Start (Complet)

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
