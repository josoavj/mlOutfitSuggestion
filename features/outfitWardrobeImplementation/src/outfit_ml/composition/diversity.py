"""Étape 4 — re-ranking diversité (voir spec, section 6).

Implémentation type MMR : à chaque tour, on sélectionne le candidat qui
maximise (score - lambda * similarité_max_avec_déjà_sélectionnés),
la similarité étant mesurée par le chevauchement d'items (Jaccard) et
pondérée par la récence de last_suggested_at.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import OutfitCombination

DIVERSITY_LAMBDA = 0.5
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


def diversify(candidates: list[OutfitCombination], top_k: int) -> list[OutfitCombination]:
    remaining = sorted(candidates, key=lambda c: c.final_score, reverse=True)
    selected: list[OutfitCombination] = []

    while remaining and len(selected) < top_k:
        best, best_mmr = None, float("-inf")
        for candidate in remaining:
            max_similarity = max((_jaccard(candidate, s) for s in selected), default=0.0)
            recency = _recency_penalty(candidate)
            mmr = candidate.final_score - DIVERSITY_LAMBDA * max(max_similarity, recency)
            if mmr > best_mmr:
                best, best_mmr = candidate, mmr

        selected.append(best)
        remaining.remove(best)

    return selected
