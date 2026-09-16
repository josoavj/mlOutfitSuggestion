from __future__ import annotations

from pathlib import Path
from typing import Callable

import joblib
import pandas as pd

from .models import CompositionContext, OutfitCombination

ScoreFn = Callable[[OutfitCombination, CompositionContext], float]
MODEL_PATH = Path("models/outfit_ranker.joblib")

_model_cache = None


def get_model():
    global _model_cache
    if _model_cache is None and MODEL_PATH.exists():
        try:
            _model_cache = joblib.load(MODEL_PATH)
        except Exception:  # noqa: BLE001
            pass
    return _model_cache


def heuristic_score(combination: OutfitCombination, context: CompositionContext) -> float:
    favorite_bonus = sum(0.1 for item in combination.items if item.is_favorite)
    formality_penalty = sum(
        abs(item.formality_level - context.dominant_occasion_formality) * 0.05
        for item in combination.items
    )
    return max(0.0, combination.compatibility_score + favorite_bonus - formality_penalty)


def ml_combination_score(combination: OutfitCombination, context: CompositionContext) -> float:
    """Scoring basé sur le modèle ML réentraîné sur les combinaisons (Phase 2)."""
    model = get_model()
    if not model:
        return heuristic_score(combination, context)

    # Identification des items par catégorie
    top = next((i for i in combination.items if i.category.value == "top"), None)
    bottom = next((i for i in combination.items if i.category.value == "bottom"), None)
    shoes = next((i for i in combination.items if i.category.value == "shoes"), None)

    # Si la combinaison n'est pas complète (Top+Bas+Chaussures), on replie sur l'heuristique
    if not (top and bottom and shoes):
        return heuristic_score(combination, context)

    f_vals = [i.formality_level for i in combination.items]
    max_f_gap = max(f_vals) - min(f_vals)
    avg_w = sum(i.warmth_rating for i in combination.items) / len(combination.items)

    row = {
        "age": context.age,
        "height_cm": context.height_cm,
        "gender": context.gender,
        "body_shape": context.body_shape,
        "occasion": context.occasion,
        "weather": context.weather_bucket,
        "top_color": top.color_primary.value,
        "top_formality": top.formality_level,
        "top_warmth": top.warmth_rating,
        "top_pattern": top.pattern.value if top.pattern else "uni",
        "bottom_color": bottom.color_primary.value,
        "bottom_formality": bottom.formality_level,
        "bottom_warmth": bottom.warmth_rating,
        "bottom_pattern": bottom.pattern.value if bottom.pattern else "uni",
        "shoes_color": shoes.color_primary.value,
        "shoes_formality": shoes.formality_level,
        "shoes_warmth": shoes.warmth_rating,
        "shoes_pattern": shoes.pattern.value if shoes.pattern else "uni",
        "max_formality_gap": max_f_gap,
        "avg_warmth": avg_w,
    }

    try:
        df = pd.DataFrame([row])
        # Retourne la probabilité de la classe 1 (pertinent)
        return float(model.predict_proba(df)[0][1])
    except Exception:  # noqa: BLE001
        return heuristic_score(combination, context)


def score_candidates(
    candidates: list[OutfitCombination],
    context: CompositionContext,
    score_fn: ScoreFn = ml_combination_score,
) -> list[OutfitCombination]:
    for candidate in candidates:
        candidate.ml_score = score_fn(candidate, context)
        candidate.final_score = candidate.ml_score
    return candidates
