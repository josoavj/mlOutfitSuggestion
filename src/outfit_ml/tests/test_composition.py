import pytest
from ..composition.filters import passes_hard_filters, filter_wardrobe
from ..composition.models import CompositionContext
from ..composition.generator import generate_candidates
from ..composition.engine import compose_outfits
from ..wardrobe.models import WardrobeItem, Category, Color, Pattern, Season


def test_composition_filters_and_generator():
    """Test complet de la génération de tenues, filtres durs et orchestration."""
    context = CompositionContext(
        weather_bucket="hot",
        target_warmth=1,
        dominant_occasion_formality=2,
        formality_tolerance=1,
        season=Season.ete
    )

    top_item = WardrobeItem(
        item_id="top_1",
        user_id="u1",
        category=Category.top,
        subcategory="t_shirt",
        color_primary=Color.blanc,
        formality_level=2,
        warmth_rating=1,
        season_suitability=[Season.ete]
    )

    bottom_item = WardrobeItem(
        item_id="bottom_1",
        user_id="u1",
        category=Category.bottom,
        subcategory="short",
        color_primary=Color.beige,
        formality_level=2,
        warmth_rating=1,
        season_suitability=[Season.ete]
    )

    shoes_item = WardrobeItem(
        item_id="shoes_1",
        user_id="u1",
        category=Category.shoes,
        subcategory="baskets",
        color_primary=Color.blanc,
        formality_level=2,
        warmth_rating=1,
        season_suitability=[Season.ete]
    )

    items = [top_item, bottom_item, shoes_item]

    # Test des filtres durs
    filtered = filter_wardrobe(items, context)
    assert len(filtered) == 3

    # Test de la génération de combinaisons valides
    candidates = generate_candidates(filtered)
    assert isinstance(candidates, list)

    # Test de l'orchestration complète du moteur de composition
    outfits = compose_outfits(items=items, context=context, top_k=2)
    assert isinstance(outfits, list)
