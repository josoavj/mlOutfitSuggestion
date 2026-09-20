"""Exécute le raisonneur HermiT UNE FOIS (offline, au build/déploiement — pas
à chaque requête de l'API) et exporte les inférences utiles dans des fichiers
JSON légers que l'app lit ensuite sans dépendance à Java/owlready2 au runtime.

Pourquoi offline et pas en live dans l'API :
- Le raisonnement DL (HermiT) prend ~1.5 s sur cette ontologie pourtant
  petite, plus le coût de démarrage de la JVM à chaque appel — totalement
  incompatible avec un endpoint /recommend appelé à chaque affichage du
  miroir.
- L'ontologie ne change pas à chaque requête (contrairement à la garde-robe
  d'un utilisateur) — la reraisonner à chaque fois n'a aucun sens.

Usage :
    python -m ontology.export_rules

Régénère data/ontology_derived/*.json à chaque modification de
ontology/outfit_ontology.py (à intégrer en CI, voir docs/ontologie.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from owlready2 import AllDifferent, sync_reasoner_hermit

from .outfit_ontology import ALL_COLORS, build_ontology

OUTPUT_DIR = Path("data/ontology_derived")


def export() -> None:
    onto = build_ontology()

    with onto:
        # Individus de sonde temporaires — un par couleur, jamais sauvegardés
        # dans le fichier .owl final — juste pour faire circuler la relation
        # symétrique harmonizesWith à travers le raisonneur de façon exhaustive.
        probes = {}
        for name in ALL_COLORS:
            probe = onto.Garment(f"_probe_{name}")
            probe.hasPrimaryColor = [getattr(onto, name)]
            probes[name] = probe

        # Sans ceci, HermiT reste en sémantique "monde ouvert" : deux
        # individus nommés distincts ne sont PAS supposés différents par
        # défaut, donc DifferentFrom(?g1, ?g2) dans la règle SWRL ne se
        # déclenche jamais et aucune paire n'est inférée. C'est LE piège
        # classique en OWL/SWRL — à ne pas oublier à chaque nouveau lot
        # d'individus créés pour interroger une règle symétrique.
        AllDifferent(list(probes.values()))

    sync_reasoner_hermit(infer_property_values=True)

    # -- 1. Compatibilité couleur, dérivée des sondes ------------------------
    color_pairs: set[tuple[str, str]] = set()
    for name, probe in probes.items():
        for other in probe.colorCompatibleWith:
            other_name = other.name.replace("_probe_", "")
            color_pairs.add(tuple(sorted((name, other_name))))

    # -- 2. Formalité minimale par occasion -----------------------------------
    occasion_formality = {
        ind.name: ind.requiresMinFormality[0]
        for ind in onto.Occasion.instances()
        if ind.requiresMinFormality
    }

    # -- 3. Classes de garment définies (pour documentation / tests) --------
    defined_classes = [
        "CasualGarment", "FormalGarment", "WarmGarment", "LightGarment",
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with (OUTPUT_DIR / "color_compatibility.json").open("w", encoding="utf-8") as f:
        json.dump([list(pair) for pair in sorted(color_pairs)], f, ensure_ascii=False, indent=2)

    with (OUTPUT_DIR / "occasion_formality.json").open("w", encoding="utf-8") as f:
        json.dump(occasion_formality, f, ensure_ascii=False, indent=2)

    print(f"{len(color_pairs)} paires de couleurs compatibles exportées")
    print(f"{len(occasion_formality)} occasions exportées : {occasion_formality}")
    print(f"Classes définies disponibles dans l'ontologie : {defined_classes}")


if __name__ == "__main__":
    export()
