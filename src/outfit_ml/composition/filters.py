"""Étape 1 du moteur de composition — filtres durs, déterministes.

Élimine les items incompatibles avec le contexte avant toute tentative
de composition. Voir spec, section 4, étape 1.
"""

from __future__ import annotations

from ..wardrobe.models import WardrobeItem
from .models import CompositionContext

WARMTH_TOLERANCE = 1  # écart toléré entre warmth_rating de l'item et target_warmth


def passes_hard_filters(item: WardrobeItem, context: CompositionContext) -> bool:
    # Filtre chaleur (si au moins une note de l'item est dans la plage de tolérance)
    if not any(abs(w - context.target_warmth) <= WARMTH_TOLERANCE for w in item.warmth_ratings):
        return False

    # Filtre formalité (si au moins une note est dans la plage de tolérance)
    if not any(abs(f - context.dominant_occasion_formality) <= context.formality_tolerance for f in item.formality_levels):
        return False

    if context.season and item.season_suitability and context.season not in item.season_suitability:
        return False

    # Filtre par sexe
    if context.gender != "unknown":
        item_target = "masculin" if context.gender == "male" else "feminin"
        if item.gender.value != "unisex" and item.gender.value != item_target:
            return False

    return True


def filter_wardrobe(items: list[WardrobeItem], context: CompositionContext) -> list[WardrobeItem]:
    return [item for item in items if passes_hard_filters(item, context)]
