"""Point d'entrée du moteur de composition — orchestre les 4 étapes
décrites dans wardrobe-composition-spec.md, section 4.

Usage attendu depuis les endpoints /recommend* existants (à adapter
selon la signature exacte de ces endpoints dans api.py) :

    from .composition.engine import compose_outfits

    combinations = compose_outfits(
        items=wardrobe_store.list_items(user_id),
        context=context,
        top_k=payload.top_k,
    )
    wardrobe_store.mark_suggested(
        user_id, [item_id for c in combinations for item_id in c.item_ids]
    )
"""

from __future__ import annotations

from ..monitoring import summarize_scores
from ..wardrobe.models import WardrobeItem
from .diversity import diversify
from .filters import filter_wardrobe
from .generator import generate_candidates
from .models import CompositionContext, OutfitCombination
from .scoring import ScoreFn, heuristic_score, score_candidates


def compose_outfits(
    items: list[WardrobeItem],
    context: CompositionContext,
    top_k: int = 3,
    score_fn: ScoreFn = heuristic_score,
    stats: dict | None = None,
) -> list[OutfitCombination]:
    # Étape 1 — filtres durs
    filtered_items = filter_wardrobe(items, context)

    # Étape 2 — génération + compatibilité
    candidates = generate_candidates(filtered_items)
    if stats is not None:
        stats["n_candidates"] = len(candidates)

    if not candidates:
        return []

    # Étape 3 — scoring
    scored = score_candidates(candidates, context, score_fn=score_fn)
    if stats is not None:
        stats.update(summarize_scores([c.final_score for c in scored]))
        stats["ml_fallbacks"] = sum(1 for c in scored if getattr(c, "scored_by", "ml") != "ml")

    # Étape 4 — diversité anti-répétition
    return diversify(scored, top_k=top_k)
