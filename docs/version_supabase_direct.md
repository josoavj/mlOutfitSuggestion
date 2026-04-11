# Version Supabase Direct

## Objectif

Brancher le service ML directement a Supabase (sans backend intermediaire) pour lire profil et agenda.

## Quand utiliser cette option

- utile pour un POC rapide
- utile si tu n'as pas encore de backend proxy

Pour la production, l'option backend MagicMirror reste recommandee pour securite et gouvernance.

## Configuration

1. Copier la config de base:

```bash
cp .env.magicmirror.example .env
```

2. Activer Supabase direct dans `.env`:

```env
MAGICMIRROR_DATA_SOURCE=supabase
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
# ou SUPABASE_ANON_KEY=... si permissions adaptees

SUPABASE_PROFILE_TABLE=profiles
SUPABASE_PROFILE_USER_ID_COLUMN=user_id

SUPABASE_AGENDA_TABLE=agenda_events
SUPABASE_AGENDA_USER_ID_COLUMN=user_id
SUPABASE_AGENDA_DATE_COLUMN=start_at
SUPABASE_AGENDA_TODAY_ONLY=true
SUPABASE_AGENDA_TITLE_COLUMN=title
SUPABASE_AGENDA_CATEGORY_COLUMN=category
SUPABASE_AGENDA_TAGS_COLUMN=tags
```

3. Lancer l'API:

```bash
uvicorn src.outfit_ml.api:app --reload
```

## Contrat minimal des tables Supabase

### profiles

Colonnes minimales:
- user_id
- gender
- age
- height_cm
- clothing_size
- top_size
- bottom_size
- shoe_size
- style_preferences (json/array ou texte parseable)
- body_shape (optionnel)
- body_measurements (json optionnel)
- location (ou city)

### agenda_events

Colonnes minimales:
- user_id
- start_at
- title (ou mapping via SUPABASE_AGENDA_TITLE_COLUMN)
- category (ou mapping via SUPABASE_AGENDA_CATEGORY_COLUMN)
- tags (ou mapping via SUPABASE_AGENDA_TAGS_COLUMN)

## Endpoints recommandes

- POST /recommend/auto
- POST /mirror/recommend-from-camera
- POST /feedback/events

## Notes securite

- eviter d'exposer la SERVICE_ROLE_KEY dans des clients mobiles/web
- preferer service ML backend uniquement
- limiter les droits si utilisation ANON_KEY

## Mapping recommande pour ton schema actuel

Pour le schema que tu as partage (`profiles` + `agenda_events`), utilise ce mapping:

```env
MAGICMIRROR_DATA_SOURCE=supabase

SUPABASE_PROFILE_TABLE=profiles
SUPABASE_PROFILE_USER_ID_COLUMN=user_id
SUPABASE_PROFILE_GENDER_COLUMN=gender
SUPABASE_PROFILE_AGE_COLUMN=age
SUPABASE_PROFILE_HEIGHT_COLUMN=height_cm
SUPABASE_PROFILE_BODY_SHAPE_COLUMN=morphology
SUPABASE_PROFILE_STYLE_PREFERENCES_COLUMN=preferred_styles
SUPABASE_PROFILE_LOCATION_COLUMN=location

SUPABASE_AGENDA_TABLE=agenda_events
SUPABASE_AGENDA_USER_ID_COLUMN=user_id
SUPABASE_AGENDA_DATE_COLUMN=start_time
SUPABASE_AGENDA_TITLE_COLUMN=title
SUPABASE_AGENDA_CATEGORY_COLUMN=event_type
SUPABASE_AGENDA_TAGS_COLUMN=description
```

Notes:
- `morphology` est normalise automatiquement vers `hourglass|rectangle|pear|inverted_triangle|oval|unknown`.
- `preferred_styles` peut etre un tableau Supabase et sera converti en liste de styles.
- `description` est acceptee comme tags source (si texte simple, il est transforme en une entree).
