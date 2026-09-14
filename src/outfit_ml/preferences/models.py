"""Modèles Pydantic pour les préférences utilisateur.

Reprend le schéma défini dans preferences-questionnaire-spec.md (section 2).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ..wardrobe.models import Color


class ToleranceMeteo(str, Enum):
    frileux = "frileux"
    neutre = "neutre"
    resistant = "resistant"


class UserPreferences(BaseModel):
    user_id: str

    styles_aimes: list[str] = Field(default_factory=list)
    styles_evites: list[str] = Field(default_factory=list)
    couleurs_aimees: list[Color] = Field(default_factory=list)
    couleurs_evitees: list[Color] = Field(default_factory=list)
    niveau_formalite_prefere: Optional[int] = Field(None, ge=1, le=5)
    items_bannis: list[str] = Field(default_factory=list)
    tolerance_meteo: ToleranceMeteo = ToleranceMeteo.neutre

    onboarding_completed_at: Optional[datetime] = None
    last_micro_survey_at: Optional[datetime] = None
    preferences_version: int = 0


class OnboardingSubmission(BaseModel):
    """Payload de PUT /preferences/{user_id} après le questionnaire initial
    (voir spec, section 3 — les 6 questions)."""

    styles_aimes: list[str] = Field(default_factory=list)
    styles_evites: list[str] = Field(default_factory=list)
    couleurs_aimees: list[Color] = Field(default_factory=list)
    couleurs_evitees: list[Color] = Field(default_factory=list)
    niveau_formalite_prefere: int = Field(..., ge=1, le=5)
    tolerance_meteo: ToleranceMeteo = ToleranceMeteo.neutre


class PreferencesPatch(BaseModel):
    """Mise à jour partielle — utilisée après un micro-questionnaire."""

    styles_aimes: Optional[list[str]] = None
    styles_evites: Optional[list[str]] = None
    couleurs_aimees: Optional[list[Color]] = None
    couleurs_evitees: Optional[list[Color]] = None
    niveau_formalite_prefere: Optional[int] = Field(None, ge=1, le=5)
    items_bannis: Optional[list[str]] = None
    tolerance_meteo: Optional[ToleranceMeteo] = None


class MicroSurveyKind(str, Enum):
    ban_item = "ban_item"
    style_check = "style_check"
    formality_check = "formality_check"
    color_check = "color_check"


class MicroSurveyResponse(BaseModel):
    """Payload de POST /preferences/{user_id}/micro-survey."""

    kind: MicroSurveyKind
    item_id: Optional[str] = None  # requis pour kind == ban_item
    accepted: bool  # ex: "oui, arrête de me le proposer" -> True
    freeform_answer: Optional[str] = None  # réponse libre si applicable
