# Documentation

Nouveautes importantes à connaître:

- Le contrat de réponse des endpoints de recommandation inclut `resolved_context`.
- Le mode auto supporte des overrides de profil/tailles/agenda.
- Le modèle utilise des features de tailles (haut, bas, chaussures) pour le ranking.
- Le dashboard technique (`/dashboard/technical`) inclut un bloc feedback.

- `quickstart.md`: démarrage complet en quelques minutes.
- `flutter_android_integration.md`: guide complet d'intégration Flutter Android + camera + endpoint unifie.
- `model_complete_documentation.md`: documentation technique complète du modèle ML (paramètres, pipeline, métriques, tuning).
- `dataset_blueprint.md`: schéma dataset complet, dictionnaire de données et règles de qualité.
- `informations_utiles.md`: guide operationnel condensé (variables, endpoints, commandes, QA, dépannage).
- `version_locale.md`: configuration et usage en mode local (fichiers JSON).
- `version_magicmirror.md`: configuration et usage en mode intégration backend MagicMirror.
- `version_supabase_direct.md`: configuration directe Supabase (sans backend intermédiaire).

Script utilitaire:

- `python -m src.outfit_ml.export_parquet`: export CSV vers Parquet partitionné par date.
