"""Étape 3 du moteur de composition — scoring.

IMPORTANT : ceci n'entraîne pas un nouveau modèle ML. `outfit_ranker.joblib`
était entraîné sur des tenues prédéfinies (liste fixe) — il ne peut pas
scorer directement des combinaisons générées dynamiquement à partir
d'items individuels tant qu'il n'est pas réentraîné sur des features de
combinaison (agrégats des items + contexte + préférences).

En attendant ce réentraînement, `heuristic_score` fournit un scoring de
repli explicite et transparent, pour que le pipeline reste utilisable de
bout en bout. Remplacer `score_fn` par un appel au ranker réentraîné dès
qu'il est disponible — l'interface (une fonction OutfitCombination,
CompositionContext -> float) ne change pas.
"""

from __future__ import annotations

from typing import Callable

from .models import CompositionContext, OutfitCombination

ScoreFn = Callable[[OutfitCombination, CompositionContext], float]


def heuristic_score(combination: OutfitCombination, context: CompositionContext) -> float:
    favorite_bonus = sum(0.1 for item in combination.items if item.is_favorite)
    formality_penalty = sum(
        abs(item.formality_level - context.dominant_occasion_formality) * 0.05
        for item in combination.items
    )
    return max(0.0, combination.compatibility_score + favorite_bonus - formality_penalty)


def score_candidates(
    candidates: list[OutfitCombination],
    context: CompositionContext,
    score_fn: ScoreFn = heuristic_score,
) -> list[OutfitCombination]:
    for candidate in candidates:
        candidate.ml_score = score_fn(candidate, context)
        candidate.final_score = candidate.ml_score
    return candidates
