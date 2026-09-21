"""Évalue l'ontologie : métriques structurelles, cohérence logique, et
réponses aux questions de compétence définies pour ce domaine.

Méthodologie : questions de compétence (Grüninger & Fox) — on définit à
l'avance les questions auxquelles l'ontologie doit pouvoir répondre, puis on
vérifie effectivement qu'elle y répond, plutôt que d'évaluer "à l'œil".

Usage :
    python -m ontology.evaluate
"""

from __future__ import annotations

from owlready2 import default_world, sync_reasoner_hermit

from .outfit_ontology import build_ontology


def structural_metrics(onto) -> dict:
    classes = list(onto.classes())
    obj_props = list(onto.object_properties())
    data_props = list(onto.data_properties())
    individuals = list(onto.individuals())

    def depth(cls, seen=None) -> int:
        seen = seen or set()
        if cls in seen:
            return 0  # cycle de sécurité — ne devrait jamais arriver ici
        seen.add(cls)
        parents = [p for p in cls.is_a if p in classes]
        if not parents:
            return 1
        return 1 + max(depth(p, seen) for p in parents)

    max_depth = max((depth(c) for c in classes), default=0)

    return {
        "classes": len(classes),
        "object_properties": len(obj_props),
        "data_properties": len(data_props),
        "individuals": len(individuals),
        "defined_classes_with_equivalent_to": sum(1 for c in classes if c.equivalent_to),
        "disjointness_axioms": len(list(onto.disjoint_classes())),
        "swrl_rules": len(list(onto.rules())),
        "max_class_hierarchy_depth": max_depth,
    }


def check_consistency(onto) -> dict:
    """Lance le raisonneur et vérifie l'absence de classes insatisfiables
    (equivalent_to owl:Nothing) — le test de cohérence logique standard."""
    try:
        sync_reasoner_hermit(infer_property_values=True)
    except Exception as e:  # OwlReadyInconsistentOntologyError si incohérente
        return {"consistent": False, "error": str(e)}

    unsatisfiable = list(default_world.inconsistent_classes())
    return {
        "consistent": len(unsatisfiable) == 0,
        "unsatisfiable_classes": [c.name for c in unsatisfiable],
    }


def competency_questions(onto) -> list[dict]:
    """Chaque question est vérifiée par une requête réelle sur l'ontologie
    raisonnée, pas décrite en théorie."""
    results = []

    # CQ1 — Quelles couleurs sont compatibles avec le bleu marine (asserté) ?
    bleu_marine = onto.BleuMarine
    harmonizes = sorted(c.name for c in bleu_marine.harmonizesWith)
    results.append({
        "question": "Quelles couleurs s'harmonisent avec BleuMarine ?",
        "answer": harmonizes,
        "pass": "Rouge" in harmonizes and "Noir" in harmonizes,
    })

    # CQ2 — Un garment de formalityLevel=[5] est-il classé FormalGarment
    # automatiquement, sans avoir jamais été explicitement tagué comme tel ?
    with onto:
        probe = onto.Garment("_cq2_probe")
        probe.formalityLevel = [5]
    sync_reasoner_hermit(infer_property_values=True)
    is_formal = onto.FormalGarment in probe.INDIRECT_is_a
    results.append({
        "question": "Un item avec formalityLevel=5 est-il classé FormalGarment par inférence ?",
        "answer": is_formal,
        "pass": is_formal,
    })

    # CQ3 — Quelle est la formalité minimale requise pour une réunion ?
    meeting_formality = onto.Meeting.requiresMinFormality[0] if onto.Meeting.requiresMinFormality else None
    results.append({
        "question": "Quelle formalité minimale pour l'occasion Meeting ?",
        "answer": meeting_formality,
        "pass": meeting_formality == 4,
    })

    # CQ4 — Top et Bottom sont-ils bien déclarés mutuellement exclusifs ?
    disjoint_ok = any(
        {onto.Top, onto.Bottom}.issubset(set(group.entities))
        for group in onto.disjoint_classes()
    )
    results.append({
        "question": "Top et Bottom sont-ils bien déclarés mutuellement exclusifs ?",
        "answer": disjoint_ok,
        "pass": disjoint_ok,
    })

    return results


if __name__ == "__main__":
    onto = build_ontology()

    print("## Métriques structurelles (avant raisonnement)\n")
    for key, value in structural_metrics(onto).items():
        print(f"- {key}: {value}")

    print("\n## Cohérence logique\n")
    consistency = check_consistency(onto)
    print(f"- Cohérente : {consistency['consistent']}")
    if not consistency["consistent"]:
        print(f"- Détail : {consistency}")

    print("\n## Questions de compétence\n")
    for cq in competency_questions(onto):
        status = "PASS" if cq["pass"] else "FAIL"
        print(f"- [{status}] {cq['question']}")
        print(f"    -> {cq['answer']}")
