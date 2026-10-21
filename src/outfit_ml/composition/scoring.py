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


def _build_feature_row(combination: OutfitCombination, context: CompositionContext) -> dict | None:
    top = next((i for i in combination.items if i.category.value == "top" or i.category.value == "dress"), None)
    bottom = next((i for i in combination.items if i.category.value == "bottom" or i.category.value == "dress"), None)
    shoes = next((i for i in combination.items if i.category.value == "shoes"), None)

    if not (top and bottom and shoes):
        return None

    f_vals = [
        min(i.formality_levels, key=lambda x: abs(x - context.dominant_occasion_formality))
        if i.formality_levels else context.dominant_occasion_formality
        for i in combination.items
    ]
    max_f_gap = max(f_vals) - min(f_vals) if f_vals else 0

    w_vals = [
        min(i.warmth_ratings, key=lambda x: abs(x - context.target_warmth))
        if i.warmth_ratings else context.target_warmth
        for i in combination.items
    ]
    avg_w = sum(w_vals) / len(w_vals) if w_vals else context.target_warmth

    top_f = min(top.formality_levels, key=lambda x: abs(x - context.dominant_occasion_formality)) if top.formality_levels else context.dominant_occasion_formality
    top_w = min(top.warmth_ratings, key=lambda x: abs(x - context.target_warmth)) if top.warmth_ratings else context.target_warmth

    bot_f = min(bottom.formality_levels, key=lambda x: abs(x - context.dominant_occasion_formality)) if bottom.formality_levels else context.dominant_occasion_formality
    bot_w = min(bottom.warmth_ratings, key=lambda x: abs(x - context.target_warmth)) if bottom.warmth_ratings else context.target_warmth

    shoe_f = min(shoes.formality_levels, key=lambda x: abs(x - context.dominant_occasion_formality)) if shoes.formality_levels else context.dominant_occasion_formality
    shoe_w = min(shoes.warmth_ratings, key=lambda x: abs(x - context.target_warmth)) if shoes.warmth_ratings else context.target_warmth

    return {
        "age": context.age or 30,
        "height_cm": context.height_cm or 170,
        "gender": context.gender or "unknown",
        "body_shape": context.body_shape or "unknown",
        "occasion": context.occasion or "casual",
        "weather": context.weather_bucket or "mild",
        "top_color": top.color_primary.value,
        "top_formality": top_f,
        "top_warmth": top_w,
        "top_pattern": top.pattern.value if top.pattern else "uni",
        "bottom_color": bottom.color_primary.value,
        "bottom_formality": bot_f,
        "bottom_warmth": bot_w,
        "bottom_pattern": bottom.pattern.value if bottom.pattern else "uni",
        "shoes_color": shoes.color_primary.value,
        "shoes_formality": shoe_f,
        "shoes_warmth": shoe_w,
        "shoes_pattern": shoes.pattern.value if shoes.pattern else "uni",
        "max_formality_gap": max_f_gap,
        "avg_warmth": avg_w,
    }


def heuristic_score(combination: OutfitCombination, context: CompositionContext) -> float:
    favorite_bonus = sum(0.1 for item in combination.items if item.is_favorite)

    total_formality_penalty = 0.0
    for item in combination.items:
        if item.formality_levels:
            closest_f = min(item.formality_levels, key=lambda x: abs(x - context.dominant_occasion_formality))
            total_formality_penalty += abs(closest_f - context.dominant_occasion_formality) * 0.05

    return max(0.0, combination.compatibility_score + favorite_bonus - total_formality_penalty)


def ml_combination_score(combination: OutfitCombination, context: CompositionContext) -> float:
    """Scoring individuel pour rétro-compatibilité."""
    row = _build_feature_row(combination, context)
    model = get_model()
    if not model or not row:
        return heuristic_score(combination, context)

    try:
        df = pd.DataFrame([row])
        return float(model.predict_proba(df)[0][1])
    except Exception:  # noqa: BLE001
        return heuristic_score(combination, context)


def score_candidates(
    candidates: list[OutfitCombination],
    context: CompositionContext,
    score_fn: ScoreFn = ml_combination_score,
) -> list[OutfitCombination]:
    model = get_model() if score_fn == ml_combination_score else None

    if model:
        rows = []
        valid_indices = []
        for idx, candidate in enumerate(candidates):
            row = _build_feature_row(candidate, context)
            if row:
                rows.append(row)
                valid_indices.append(idx)
            else:
                candidate.ml_score = heuristic_score(candidate, context)

        if rows:
            try:
                df_all = pd.DataFrame(rows)
                probas = model.predict_proba(df_all)[:, 1]
                for idx, prob in zip(valid_indices, probas):
                    candidates[idx].ml_score = float(prob)
            except Exception:  # noqa: BLE001
                for idx in valid_indices:
                    candidates[idx].ml_score = heuristic_score(candidates[idx], context)
    else:
        for candidate in candidates:
            candidate.ml_score = score_fn(candidate, context)

    # Calcul du score composite équilibré
    for candidate in candidates:
        favorite_bonus = sum(0.1 for item in candidate.items if item.is_favorite)
        ml_weight = candidate.ml_score if candidate.ml_score is not None else 0.5
        compat_weight = candidate.compatibility_score

        # Composition du score : 30% ML, 40% Compatibilité Ontologie/RAG, 30% Favoris
        candidate.final_score = (0.3 * ml_weight) + (0.5 * compat_weight) + min(0.2, favorite_bonus)

    return candidates
