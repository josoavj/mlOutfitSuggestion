"""Tests unitaires de validation des correctifs de composition et de recommandation."""

import random
from pathlib import Path

from ..composition.diversity import diversify
from ..composition.filters import passes_hard_filters, filter_wardrobe
from ..composition.generator import generate_candidates
from ..composition.models import CompositionContext, OutfitCombination
from ..composition.scoring import ml_combination_score, score_candidates
from ..wardrobe.models import Category, Color, Pattern, Season, WardrobeItem


def test_generator_unbiased_candidate_sampling():
    """Vérifie que l'échantillonnage ne bloque pas sur les 2 premiers hauts."""
    items = []
    # 10 Hauts, 10 Bas, 10 Chaussures
    for i in range(10):
        items.append(WardrobeItem(item_id=f"top_{i}", user_id="u", category=Category.top, subcategory="chemise", color_primary=Color.noir, formality_levels=[3], warmth_ratings=[3]))
        items.append(WardrobeItem(item_id=f"bot_{i}", user_id="u", category=Category.bottom, subcategory="pantalon", color_primary=Color.bleu_marine, formality_levels=[3], warmth_ratings=[3]))
        items.append(WardrobeItem(item_id=f"shoe_{i}", user_id="u", category=Category.shoes, subcategory="baskets", color_primary=Color.blanc, formality_levels=[3], warmth_ratings=[3]))

    # Avec 10x10x10 = 1000 combinaisons et max_candidates=500, l'ancien générateur ne voyait que 5 hauts
    candidates = generate_candidates(items, max_candidates=500, rng=random.Random(42))
    tops_seen = len({c.items[0].item_id for c in candidates})

    # Avec l'échantillonnage uniforme, presque tous les 10 hauts sont représentés
    assert tops_seen >= 8


def test_thermal_layering_hard_filter():
    """Vérifie que les t-shirts légers (chaleur 2) passent les filtres par temps froid (cible 5) grâce au layering."""
    light_top = WardrobeItem(
        item_id="light_tshirt", user_id="u", category=Category.top, subcategory="t-shirt",
        color_primary=Color.blanc, formality_levels=[2], warmth_ratings=[2]
    )
    context_cold = CompositionContext(
        weather_bucket="cold", target_warmth=5, dominant_occasion_formality=2, formality_tolerance=1, user_id="u"
    )

    # Doit passer grâce à BASE_WARMTH_TOLERANCE = 2 (5 - 2 = 3 <= 2)
    assert passes_hard_filters(light_top, context_cold) is True


def test_batched_scoring_and_composite_score():
    """Vérifie le calcul du score composite et le comportement sans NaN."""
    items = [
        WardrobeItem(item_id="top_1", user_id="u", category=Category.top, subcategory="chemise", color_primary=Color.blanc, formality_levels=[3], warmth_ratings=[3]),
        WardrobeItem(item_id="bot_1", user_id="u", category=Category.bottom, subcategory="pantalon", color_primary=Color.noir, formality_levels=[3], warmth_ratings=[3]),
        WardrobeItem(item_id="shoe_1", user_id="u", category=Category.shoes, subcategory="mocassins", color_primary=Color.marron, formality_levels=[3], warmth_ratings=[3]),
    ]
    context = CompositionContext(
        weather_bucket="mild", target_warmth=3, dominant_occasion_formality=3, formality_tolerance=1, user_id="u", age=30, height_cm=170, gender="male"
    )

    candidates = generate_candidates(items, max_candidates=10)
    scored = score_candidates(candidates, context)

    assert len(scored) > 0
    assert 0.0 <= scored[0].final_score <= 1.0


def test_mmr_min_max_normalization():
    """Vérifie que le re-ranking MMR normalise les scores et ne renvoie pas d'erreur sur liste finie."""
    top = WardrobeItem(item_id="top_1", user_id="u", category=Category.top, subcategory="chemise", color_primary=Color.blanc, formality_levels=[3], warmth_ratings=[3])
    bot = WardrobeItem(item_id="bot_1", user_id="u", category=Category.bottom, subcategory="pantalon", color_primary=Color.noir, formality_levels=[3], warmth_ratings=[3])
    shoe = WardrobeItem(item_id="shoe_1", user_id="u", category=Category.shoes, subcategory="mocassins", color_primary=Color.marron, formality_levels=[3], warmth_ratings=[3])

    c1 = OutfitCombination(items=[top, bot, shoe], compatibility_score=0.9)
    c1.final_score = 0.85
    c2 = OutfitCombination(items=[top, bot, shoe], compatibility_score=0.8)
    c2.final_score = 0.84

    diversified = diversify([c1, c2], top_k=2)
    assert len(diversified) == 2
    assert diversified[0] is c1
