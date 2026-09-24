# Documentation

Nouveautes importantes à connaître:

- Le contrat de réponse des endpoints de recommandation inclut `resolved_context`.
- Le mode auto supporte des overrides de profil/tailles/agenda.
- Le modèle utilise des features de tailles (haut, bas, chaussures) pour le ranking.
- Le dashboard technique (`/dashboard/technical`) inclut les métriques d'ontologie OWL, RAG, garde-robe et feedback.
- L'interface web inclut désormais des pages dédiées à l'Onboarding, à la Gestion de la Garde-robe, aux Métriques et à la Console API.
- Support du backend de stockage relationnel SQLite (`STORAGE_BACKEND=sqlite` dans `db_store.py`) en mode WAL haute concurrence.
- Sécurisation des clés API en temps constant (`secrets.compare_digest`), sanitisation des identifiants contre le Path Traversal et limite d'upload de 5 Mo.
- Workflow CI automatisé avec GitHub Actions (`.github/workflows/ci.yml`).

- `quickstart.md`: démarrage complet en quelques minutes.
- `flutter_android_integration.md`: guide complet d'intégration Flutter Android + camera + endpoint unifie.
- `model_complete_documentation.md`: documentation technique complète du modèle ML (paramètres, pipeline, métriques, tuning).
- `dataset_blueprint.md`: schéma dataset complet, dictionnaire de données et règles de qualité.
- `informations_utiles.md`: guide operationnel condensé (variables, endpoints, commandes, QA, dépannage).
- `version_locale.md`: configuration et usage en mode local (fichiers JSON).
- `version_magicmirror.md`: configuration et usage en mode intégration backend MagicMirror.
- `version_supabase_direct.md`: configuration directe Supabase (sans backend intermédiaire).
- `updates/wardrobespec.md`: [NEW] Phase 2 - Spécifications de la garde-robe individuelle et composition dynamique.
- `updates/preferencequestionnaire.md`: [NEW] Phase 2 - Spécifications des questionnaires de préférences et micro-questionnaires.

Script utilitaire:

- `python -m src.outfit_ml.export_parquet`: export CSV vers Parquet partitionné par date.
