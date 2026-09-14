"""Endpoints /preferences — à monter sur l'app FastAPI existante.

Dans src/outfit_ml/api.py :

    from .preferences.router import router as preferences_router
    app.include_router(preferences_router)
"""

from __future__ import annotations

from fastapi import APIRouter

from .models import (
    MicroSurveyResponse,
    OnboardingSubmission,
    PreferencesPatch,
    UserPreferences,
)
from .store import preferences_store

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/{user_id}", response_model=UserPreferences)
def get_preferences(user_id: str) -> UserPreferences:
    return preferences_store.get(user_id)


@router.put("/{user_id}", response_model=UserPreferences)
def submit_onboarding(user_id: str, payload: OnboardingSubmission) -> UserPreferences:
    return preferences_store.submit_onboarding(user_id, payload)


@router.patch("/{user_id}", response_model=UserPreferences)
def patch_preferences(user_id: str, payload: PreferencesPatch) -> UserPreferences:
    return preferences_store.patch(user_id, payload)


@router.get("/{user_id}/onboarding")
def onboarding_status(user_id: str) -> dict:
    return {"completed": preferences_store.is_onboarded(user_id)}


@router.post("/{user_id}/micro-survey", response_model=UserPreferences)
def submit_micro_survey(user_id: str, response: MicroSurveyResponse) -> UserPreferences:
    return preferences_store.apply_micro_survey_response(user_id, response)
