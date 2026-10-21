"""Étape 4 — re-ranking diversité (voir spec, section 6).

Implémentation type MMR : à chaque tour, on sélectionne le candidat qui
maximise (score - lambda * similarité_max_avec_déjà_sélectionnés),
la similarité étant mesurée par le chevauchement d'items (Jaccard) et
pondérée par la récence de last_suggested_at.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .models import OutfitCombination

DIVERSITY_LAMBDA = 0.3
RECENCY_HALF_LIFE_DAYS = 7.0


def _jaccard(a: OutfitCombination, b: OutfitCombination) -> float:
    ids_a, ids_b = set(a.item_ids), set(b.item_ids)
    if not ids_a or not ids_b:
        return 0.0
    return len(ids_a & ids_b) / len(ids_a | ids_b)


def _recency_penalty(combination: OutfitCombination) -> float:
    """Pénalise les combinaisons contenant des items récemment suggérés,
    même si elles n'ont encore jamais été sélectionnées ensemble."""
    now = datetime.now(timezone.utc)
    penalties = []
    for item in combination.items:
        if not item.last_suggested_at:
            penalties.append(0.0)
            continue
        last = item.last_suggested_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - last).total_seconds() / 86400)
        penalties.append(max(0.0, 1.0 - age_days / RECENCY_HALF_LIFE_DAYS))
    return sum(penalties) / len(penalties) if penalties else 0.0


def _structural_similarity(a: OutfitCombination, b: OutfitCombination) -> float:
    """Mesure la similarité basée sur les sous-catégories (évite d'avoir 5 fois 'Jean + Chemise')."""
    subs_a = sorted([i.subcategory for i in a.items])
    subs_b = sorted([i.subcategory for i in b.items])

    if not subs_a or not subs_b:
        return 0.0

    matches = sum(1 for s in subs_a if s in subs_b)
    return matches / max(len(subs_a), len(subs_b))


def diversify(candidates: list[OutfitCombination], top_k: int) -> list[OutfitCombination]:
    if not candidates:
        return []

    # Nettoyage anti-NaN
    for c in candidates:
        if not math.isfinite(c.final_score):
            c.final_score = 0.0

    # Normalisation Min-Max des scores candidats [0, 1]
    scores = [c.final_score for c in candidates]
    min_s, max_s = min(scores), max(scores)
    span = (max_s - min_s) if (max_s - min_s) > 1e-6 else 1.0

    rel_scores = {id(c): (c.final_score - min_s) / span for c in candidates}

    remaining = sorted(candidates, key=lambda c: c.final_score, reverse=True)
    selected: list[OutfitCombination] = []

    while remaining and len(selected) < top_k:
        best = remaining[0]
        best_mmr = float("-inf")

        for candidate in remaining:
            max_id_sim = max((_jaccard(candidate, s) for s in selected), default=0.0)
            max_struct_sim = max((_structural_similarity(candidate, s) for s in selected), default=0.0)
            recency = _recency_penalty(candidate) * 0.4  # Poids ajusté pour les suggestions

            penalty = max(max_id_sim, max_struct_sim * 0.7, recency)
            mmr = rel_scores[id(candidate)] - (DIVERSITY_LAMBDA * penalty)

            if mmr > best_mmr:
                best = candidate
                best_mmr = mmr

        selected.append(best)
        remaining.remove(best)

    return selected
