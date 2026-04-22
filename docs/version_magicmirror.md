# Version Integration MagicMirror

## Objectif

Brancher le moteur de recommandation sur l'infrastructure backend MagicMirror (profil + agenda via API).

## Configuration

1. Copier la configuration MagicMirror:

```bash
cp .env.magicmirror.example .env
```

2. Renseigner les variables backend:

- MAGICMIRROR_API_BASE_URL
- MAGICMIRROR_API_TOKEN (si securise)
- MAGICMIRROR_PROFILE_PATH_TEMPLATE
- MAGICMIRROR_AGENDA_PATH_TEMPLATE
- API_AUTH_ENABLED
- API_AUTH_KEY
- ALLOWED_ORIGINS

3. Lancer l'API:

```bash
uvicorn src.outfit_ml.api:app --reload
```

## Endpoints recommandés

- POST /recommend/auto
- POST /mirror/recommend-from-camera
- POST /feedback/events

## Test rapide

```bash
curl -X POST "http://127.0.0.1:8000/recommend/auto" \
  -H "X-API-Key: replace_with_strong_shared_secret" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u-001","top_k":3}'
```

## Liaison application (recommandé)

1. Activer la securité API (`API_AUTH_ENABLED=true`).
2. Configurer le client Flutter/MagicMirror pour envoyer `X-API-Key`.
3. Appeler en priorité `POST /mirror/recommend-from-camera`.
4. Envoyer les interactions en batch vers `POST /feedback/events`.

## Avantages

- Donnees profil/agenda temps réel
- Architecture prête pour la production
- Intégration naturelle avec app Android/Web

## Points d'attention

- Gérer timeout/retry reseau vers backend et météo
- Sécuriser les endpoints (token/JWT)
- Mettre en place monitoring des latences et erreurs
