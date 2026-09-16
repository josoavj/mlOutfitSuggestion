import pytest
from .composition.rag import style_rag
from .composition.filters import passes_hard_filters
from .composition.models import CompositionContext
from .wardrobe.models import WardrobeItem, Category, Color, Pattern, Season
from .recommend import OutfitRecommender
from .schemas import RecommendationRequest, WeatherInput


def test_rag_color_harmony():
    """Vérifie le fonctionnement du moteur StyleRAG pour l'harmonie des couleurs."""
    # Les neutres universels doivent s'accorder avec tout
    assert style_rag.check_color_harmony("noir", "rouge") is True
    assert style_rag.check_color_harmony("bleu_marine", "jaune") is True

    # Deux couleurs vives non répertoriées ensemble ou non-neutres doivent échouer ou valider selon les paires
    # 'bleu_marine' et 'rouge' est une paire complémentaire définie dans le corpus
    assert style_rag.check_color_harmony("bleu_marine", "rouge") is True


def test_composition_hard_filters():
    """Valide les filtres durs météo et formalité du moteur de composition."""
    context = CompositionContext(
        weather_bucket="cold",
        target_warmth=5,
        dominant_occasion_formality=3,
        formality_tolerance=1,
        season=Season.hiver
    )

    # Item adapté (chaud et niveau de formalité compatible)
    item_ok = WardrobeItem(
        item_id="test_1",
        user_id="u-test",
        category=Category.top,
        subcategory="pull",
        color_primary=Color.noir,
        formality_level=3,
        warmth_rating=5,
        season_suitability=[Season.hiver]
    )
    assert passes_hard_filters(item_ok, context) is True

    # Item inadapté (trop léger pour du grand froid)
    item_cold_fail = WardrobeItem(
        item_id="test_2",
        user_id="u-test",
        category=Category.top,
        subcategory="t_shirt",
        color_primary=Color.blanc,
        formality_level=3,
        warmth_rating=1,
        season_suitability=[Season.ete]
    )
    assert passes_hard_filters(item_cold_fail, context) is False


def test_recommender_integration_and_bootstrap():
    """Vérifie l'intégration complète et la génération automatique d'items (bootstrap)."""
    recommender = OutfitRecommender()
    
    # Requête pour un utilisateur sans garde-robe pré-existante (déclenche le bootstrap)
    request = RecommendationRequest(
        user_id="user_new_test",
        gender="male",
        age=30,
        height_cm=180,
        clothing_size="m",
        top_size="m",
        bottom_size="m",
        shoe_size="42",
        style_preferences=["classic", "casual"],
        agenda=["Réunion importante au bureau", "Sport ce soir"],
        location="Paris",
        weather=WeatherInput(temperature_c=8.0, condition="cloudy"),
        top_k=2
    )

    response = recommender.recommend(request)

    assert response.user_id == "user_new_test"
    assert len(response.suggestions) > 0
    assert response.weather_bucket == "cold"
    assert response.dominant_occasion == "work"
