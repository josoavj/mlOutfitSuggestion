from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Request
from ..api import require_api_key, limiter

from .models import (
    MicroSurveyResponse,
    OnboardingSubmission,
    PreferencesPatch,
    UserPreferences,
)
from .store import preferences_store

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/{user_id}", response_model=UserPreferences)
@limiter.limit(os.getenv("RATE_LIMIT_PREFERENCES", "30/minute"))
def get_preferences(
    request: Request,
    user_id: str,
    _: None = Depends(require_api_key)
) -> UserPreferences:
    return preferences_store.get(user_id)


@router.put("/{user_id}", response_model=UserPreferences)
@limiter.limit(os.getenv("RATE_LIMIT_PREFERENCES", "30/minute"))
def submit_onboarding(
    request: Request,
    user_id: str, 
    payload: OnboardingSubmission,
    _: None = Depends(require_api_key)
) -> UserPreferences:
    return preferences_store.submit_onboarding(user_id, payload)


@router.patch("/{user_id}", response_model=UserPreferences)
@limiter.limit(os.getenv("RATE_LIMIT_PREFERENCES", "30/minute"))
def patch_preferences(
    request: Request,
    user_id: str, 
    payload: PreferencesPatch,
    _: None = Depends(require_api_key)
) -> UserPreferences:
    return preferences_store.patch(user_id, payload)


@router.get("/{user_id}/onboarding")
@limiter.limit(os.getenv("RATE_LIMIT_PREFERENCES", "30/minute"))
def onboarding_status(
    request: Request,
    user_id: str,
    _: None = Depends(require_api_key)
) -> dict:
    return {"completed": preferences_store.is_onboarded(user_id)}


@router.post("/{user_id}/micro-survey", response_model=UserPreferences)
@limiter.limit(os.getenv("RATE_LIMIT_PREFERENCES", "30/minute"))
def submit_micro_survey(
    request: Request,
    user_id: str, 
    response: MicroSurveyResponse,
    _: None = Depends(require_api_key)
) -> UserPreferences:
    return preferences_store.apply_micro_survey_response(user_id, response)
