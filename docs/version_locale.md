# Version Locale

## Objectif

Utiliser le moteur de recommandation en local sans backend MagicMirror.
Le profil et l'agenda sont lus depuis des fichiers JSON locaux.

## Configuration

1. Copier la configuration locale:

```bash
cp .env.local.example .env
```

2. Verifier les fichiers de donnees locales:
- data/users/{user_id}/profile.json
- data/users/{user_id}/agenda_today.json

3. Lancer l'API:

```bash
uvicorn src.outfit_ml.api:app --reload
```

## Endpoints recommandes

- POST /recommend/auto
- POST /mirror/recommend-from-camera
- POST /feedback/events

## Test rapide

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u-001","top_k":3}'
```

## Avantages

- Setup rapide
- Pas de dependance backend externe
- Ideal dev, test, demo

## Limites

- Donnees statiques si fichiers non synchronises
- Pas de source profil/agenda temps reel
