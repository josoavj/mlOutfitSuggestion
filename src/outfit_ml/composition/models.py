from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..wardrobe.models import Season, WardrobeItem


class CompositionContext(BaseModel):
    """Contexte résolu utilisé pour filtrer/scorer les combinaisons.

    Correspond au `resolved_context` déjà produit par l'API actuelle
    (voir README, section "Contrat de réponse").
    """

    weather_bucket: str  # ex: "cold", "mild", "hot", "rain"
    target_warmth: int  # 1-5, dérivé de la météo (+ tolerance_meteo utilisateur)
    dominant_occasion_formality: int  # 1-5, dérivé de l'agenda du jour
    formality_tolerance: int = 1  # écart toléré autour de dominant_occasion_formality
    season: Optional[Season] = None
    
    # Profil utilisateur pour le scoring ML
    user_id: str = ""
    gender: str = "unknown"
    age: int = 30
    height_cm: int = 170
    body_shape: str = "unknown"
    occasion: str = "casual"


class OutfitCombination(BaseModel):
    items: list[WardrobeItem]
    compatibility_score: float = 0.0
    ml_score: float = 0.0
    final_score: float = 0.0

    @property
    def item_ids(self) -> list[str]:
        return [i.item_id for i in self.items]
