"""Étape 1 du moteur de composition — filtres durs, déterministes.

Élimine les items incompatibles avec le contexte avant toute tentative
de composition. Voir spec, section 4, étape 1.
"""

from __future__ import annotations

from ..wardrobe.models import Category, WardrobeItem
from .models import CompositionContext

OUTERWEAR_WARMTH_TOLERANCE = 1  # Tolérance stricte pour les manteaux/vestes
BASE_WARMTH_TOLERANCE = 3       # Tolérance élargie (layering) pour les hauts/bas (ex: t-shirt sous manteau)

GENDER_MAP = {
    "male": "masculin",
    "masculin": "masculin",
    "female": "feminin",
    "feminin": "feminin",
}


def passes_hard_filters(item: WardrobeItem, context: CompositionContext, relaxed: bool = False) -> bool:
    # 1. Filtre chaleur (avec layering)
    is_outer = item.category == Category.outerwear
    tol_w = (OUTERWEAR_WARMTH_TOLERANCE if is_outer else BASE_WARMTH_TOLERANCE) + (1 if relaxed else 0)

    if item.warmth_ratings:
        if not any(abs(w - context.target_warmth) <= tol_w for w in item.warmth_ratings):
            return False

    # 2. Filtre formalité
    tol_f = context.formality_tolerance + (1 if relaxed else 0)
    if item.formality_levels:
        if not any(abs(f - context.dominant_occasion_formality) <= tol_f for f in item.formality_levels):
            return False

    # 3. Filtre saison
    if context.season and item.season_suitability and context.season not in item.season_suitability:
        return False

    # 4. Filtre par sexe
    if context.gender:
        target_gender = GENDER_MAP.get(str(context.gender).lower())
        if target_gender and item.gender.value != "unisex" and item.gender.value != target_gender:
            return False

    return True


def filter_wardrobe(items: list[WardrobeItem], context: CompositionContext) -> list[WardrobeItem]:
    filtered = [item for item in items if passes_hard_filters(item, context, relaxed=False)]

    # Vérification que les catégories essentielles ne sont pas vides
    has_top = any(i.category in (Category.top, Category.dress) for i in filtered)
    has_shoes = any(i.category == Category.shoes for i in filtered)

    if not has_top or not has_shoes:
        # Relaxation progressive si les filtres initiaux sont trop stricts
        filtered = [item for item in items if passes_hard_filters(item, context, relaxed=True)]

    return filtered
