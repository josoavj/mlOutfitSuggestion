"""Étape 1 du moteur de composition — filtres durs, déterministes.

Élimine les items incompatibles avec le contexte avant toute tentative
de composition. Voir spec, section 4, étape 1.
"""

from __future__ import annotations

from ..wardrobe.models import WardrobeItem
from .models import CompositionContext

WARMTH_TOLERANCE = 1  # écart toléré entre warmth_rating de l'item et target_warmth


def passes_hard_filters(item: WardrobeItem, context: CompositionContext) -> bool:
    if abs(item.warmth_rating - context.target_warmth) > WARMTH_TOLERANCE:
        return False

    if abs(item.formality_level - context.dominant_occasion_formality) > context.formality_tolerance:
        return False

    if context.season and item.season_suitability and context.season not in item.season_suitability:
        return False

    return True


def filter_wardrobe(items: list[WardrobeItem], context: CompositionContext) -> list[WardrobeItem]:
    return [item for item in items if passes_hard_filters(item, context)]
