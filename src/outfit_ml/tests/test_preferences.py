from ..preferences.store import preferences_store
from ..preferences.models import OnboardingSubmission, ToleranceMeteo, Color


def test_preferences_onboarding_and_store():
    """Test exhaustif du questionnaire initial d'onboarding et des préférences."""
    user_id = "user_test_prefs"

    payload = OnboardingSubmission(
        styles_aimes=["classic", "minimalist"],
        styles_evites=["sport"],
        couleurs_aimees=[Color.noir, Color.bleu_marine],
        couleurs_evitees=[Color.orange],
        niveau_formalite_prefere=3,
        tolerance_meteo=ToleranceMeteo.neutre
    )

    # Validation soumission onboarding
    prefs = preferences_store.submit_onboarding(user_id, payload)
    assert prefs.user_id == user_id
    assert "classic" in prefs.styles_aimes
    assert preferences_store.is_onboarded(user_id) is True

    # Récupération
    fetched = preferences_store.get(user_id)
    assert fetched.preferences_version == 1
