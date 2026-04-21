# Documentation

Nouveautes importantes a connaitre:

- Le contrat de reponse des endpoints de recommandation inclut `resolved_context`.
- Le mode auto supporte des overrides de profil/tailles/agenda.
- Le modele utilise des features de tailles (haut, bas, chaussures) pour le ranking.
- Le dashboard technique (`/dashboard/technical`) inclut un bloc feedback.

- `quickstart.md`: demarrage complet en quelques minutes.
- `flutter_android_integration.md`: guide complet integration Flutter Android + camera + endpoint unifie.
- `model_complete_documentation.md`: documentation technique complete du modele ML (parametres, pipeline, metriques, tuning).
- `dataset_blueprint.md`: schema dataset complet, dictionnaire de donnees et regles qualite.
- `informations_utiles.md`: guide operationnel condense (variables, endpoints, commandes, QA, depannage).
- `version_locale.md`: configuration et usage en mode local (fichiers JSON).
- `version_magicmirror.md`: configuration et usage en mode integration backend MagicMirror.
- `version_supabase_direct.md`: configuration directe Supabase (sans backend intermediaire).

Script utilitaire:

- `python -m src.outfit_ml.export_parquet`: export CSV vers Parquet partitionne par date.
