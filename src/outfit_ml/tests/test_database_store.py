"""Tests unitaires pour le backend SQLite DatabaseStore."""

import pytest
from pathlib import Path

from ..db_store import DatabaseStore
from ..preferences.models import OnboardingSubmission, PreferencesPatch, MicroSurveyResponse, MicroSurveyKind
from ..wardrobe.models import Category, Color, WardrobeItemCreate, WardrobeItemUpdate
from ..wardrobe.store import WardrobeItemNotFound


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseStore:
    db_file = tmp_path / "test_app.db"
    return DatabaseStore(db_path=db_file)


def test_sqlite_wardrobe_crud(temp_db: DatabaseStore):
    user_id = "test_user_db"

    # 1. Create item
    payload = WardrobeItemCreate(
        category=Category.top,
        subcategory="t-shirt",
        color_primary=Color.noir,
        formality_levels=[2],
        warmth_ratings=[2],
    )
    item = temp_db.create_wardrobe_item(user_id, payload)
    assert item.item_id.startswith("itm_")
    assert item.category == Category.top

    # 2. List items
    items = temp_db.list_wardrobe_items(user_id)
    assert len(items) == 1
    assert items[0].item_id == item.item_id

    # 3. Get item
    fetched = temp_db.get_wardrobe_item(user_id, item.item_id)
    assert fetched.subcategory == "t-shirt"

    # 4. Update item
    updated = temp_db.update_wardrobe_item(
        user_id, item.item_id, WardrobeItemUpdate(subcategory="polo", formality_levels=[3])
    )
    assert updated.subcategory == "polo"
    assert updated.formality_levels == [3]

    # 5. Mark suggested
    temp_db.mark_wardrobe_suggested(user_id, [item.item_id])
    suggested_item = temp_db.get_wardrobe_item(user_id, item.item_id)
    assert suggested_item.last_suggested_at is not None

    # 6. Delete item
    temp_db.delete_wardrobe_item(user_id, item.item_id)
    with pytest.raises(WardrobeItemNotFound):
        temp_db.get_wardrobe_item(user_id, item.item_id)


def test_sqlite_preferences_crud(temp_db: DatabaseStore):
    user_id = "test_user_pref_db"

    # 1. Default empty preferences
    prefs = temp_db.get_preferences(user_id)
    assert prefs.user_id == user_id
    assert prefs.onboarding_completed_at is None

    # 2. Onboarding submission
    onboarding = OnboardingSubmission(
        styles_aimes=["minimalist", "classic"],
        styles_evites=["sport"],
        couleurs_aimees=["bleu_marine"],
        couleurs_evitees=["jaune"],
        niveau_formalite_prefere=3,
        tolerance_meteo="neutre",
    )
    submitted = temp_db.submit_onboarding(user_id, onboarding)
    assert submitted.onboarding_completed_at is not None
    assert submitted.styles_aimes == ["minimalist", "classic"]

    # 3. Patch preferences
    patched = temp_db.patch_preferences(
        user_id, PreferencesPatch(styles_aimes=["minimalist", "classic", "elegant"])
    )
    assert "elegant" in patched.styles_aimes
    assert patched.preferences_version == 2

    # 4. Micro-survey
    survey = MicroSurveyResponse(
        kind=MicroSurveyKind.ban_item,
        item_id="itm_banned_123",
        accepted=True,
    )
    survey_result = temp_db.apply_micro_survey_response(user_id, survey)
    assert "itm_banned_123" in survey_result.items_bannis
    assert survey_result.preferences_version == 3
