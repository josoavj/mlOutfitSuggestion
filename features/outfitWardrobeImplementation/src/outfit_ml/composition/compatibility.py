"""Étape 2 du moteur de composition — cohérence entre pièces d'une tenue.

Règles simples codées en dur pour l'instant (voir spec, section 4 étape 2
et section 5 : ces règles sont candidates à être remplacées/enrichies par
une interrogation du corpus RAG data/corpus_style/ plutôt que d'être
figées ici).
"""

from __future__ import annotations

from itertools import combinations

from ..wardrobe.models import Color, Pattern, WardrobeItem

NEUTRALS = {Color.noir, Color.blanc, Color.gris, Color.beige, Color.marron, Color.bleu_marine}

# Paires de couleurs non-neutres considérées harmonieuses (complémentaires/analogues).
# Symétrique : (A, B) implique (B, A).
COMPLEMENTARY_PAIRS = {
    (Color.bleu_marine, Color.rouge),
    (Color.bleu_clair, Color.beige),
    (Color.vert, Color.beige),
    (Color.rose, Color.gris),
    (Color.jaune, Color.bleu_marine),
    (Color.violet, Color.gris),
}

MAX_FORMALITY_GAP = 1


def _colors_compatible(c1: Color, c2: Color) -> bool:
    if c1 == c2:
        return True
    if Color.multicolore in (c1, c2):
        # Un imprimé/multicolore ne se marie bien qu'avec un neutre.
        other = c2 if c1 == Color.multicolore else c1
        return other in NEUTRALS
    if c1 in NEUTRALS or c2 in NEUTRALS:
        return True
    return (c1, c2) in COMPLEMENTARY_PAIRS or (c2, c1) in COMPLEMENTARY_PAIRS


def _patterns_compatible(p1: Pattern | None, p2: Pattern | None) -> bool:
    strong_patterns = {Pattern.imprime, Pattern.carreaux, Pattern.a_pois}
    if p1 in strong_patterns and p2 in strong_patterns:
        return False
    return True


def combination_compatibility_score(items: list[WardrobeItem]) -> float:
    """Renvoie un score entre 0 et 1 (0 = incompatible, exclu ensuite par le
    moteur). Une paire incompatible fait tomber le score à 0."""
    if len(items) < 2:
        return 1.0

    pair_scores: list[float] = []
    for a, b in combinations(items, 2):
        if abs(a.formality_level - b.formality_level) > MAX_FORMALITY_GAP:
            return 0.0
        if not _patterns_compatible(a.pattern, b.pattern):
            return 0.0

        colors_ok = _colors_compatible(a.color_primary, b.color_primary)
        pair_scores.append(1.0 if colors_ok else 0.0)

    if 0.0 in pair_scores:
        return 0.0
    return sum(pair_scores) / len(pair_scores)


def is_compatible(items: list[WardrobeItem]) -> bool:
    return combination_compatibility_score(items) > 0.0
