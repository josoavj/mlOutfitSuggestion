import pytest
from ..wardrobe.store import wardrobe_store, WardrobeItemNotFound
from ..wardrobe.models import WardrobeItemCreate, Category, Color, Pattern, Season


def test_wardrobe_store_crud_and_methods():
    """Test complet des opérations CRUD et utilitaires de la garde-robe locale."""
    user_id = "user_test_wardrobe"
    
    # Nettoyage préalable s'il y a lieu
    try:
        wardrobe_store.delete_item(user_id, "test_item_id_123")
    except Exception:
        pass

    payload = WardrobeItemCreate(
        category=Category.top,
        subcategory="chemise_luxe",
        color_primary=Color.bleu_marine,
        formality_levels=[4],
        warmth_ratings=[2],
        pattern=Pattern.uni,
        season_suitability=[Season.printemps, Season.ete]
    )

    # 1. Création d'un item
    item = wardrobe_store.create_item(user_id, payload)
    assert item.subcategory == "chemise_luxe"
    assert item.color_primary == Color.bleu_marine
    assert item.is_favorite is False

    # 2. Liste d'items
    items = wardrobe_store.list_items(user_id, category=Category.top.value)
    assert len(items) > 0
    assert any(i.subcategory == "chemise_luxe" for i in items)

    # 3. Récupération d'un item spécifique
    fetched = wardrobe_store.get_item(user_id, item.item_id)
    assert fetched.item_id == item.item_id

    # 4. Gestion des exceptions
    with pytest.raises(WardrobeItemNotFound):
        wardrobe_store.get_item(user_id, "non_existent_id")

    # 5. Marquage comme suggéré
    wardrobe_store.mark_suggested(user_id, [item.item_id])
    updated_item = wardrobe_store.get_item(user_id, item.item_id)
    assert updated_item.last_suggested_at is not None

    # Nettoyage
    wardrobe_store.delete_item(user_id, item.item_id)
