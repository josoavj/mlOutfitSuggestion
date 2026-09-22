"""Interface que composition/compatibility.py et recommend.py peuvent
utiliser au runtime — lit uniquement les JSON pré-calculés par
ontology/export_rules.py, aucune dépendance à owlready2 ni à Java ici.

Pas encore branché dans compatibility.py/recommend.py (voir docs/ontologie.md,
section « Intégration » — à faire une fois le bug §1 de l'audit corrigé, pour
ne pas mélanger deux changements dans le même diagnostic).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DERIVED_DIR = Path("data/ontology_derived")


@lru_cache(maxsize=1)
def _color_pairs() -> frozenset[frozenset[str]]:
    path = DERIVED_DIR / "color_compatibility.json"
    with path.open("r", encoding="utf-8") as f:
        pairs = json.load(f)
    return frozenset(frozenset(pair) for pair in pairs)


@lru_cache(maxsize=1)
def _occasion_formality() -> dict[str, int]:
    path = DERIVED_DIR / "occasion_formality.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def colors_harmonize(color_a: str, color_b: str) -> bool:
    """Remplace NEUTRALS/COMPLEMENTARY_PAIRS codés en dur dans compatibility.py."""
    if color_a == color_b:
        return True
    return frozenset((color_a, color_b)) in _color_pairs()


def min_formality_for_occasion(occasion: str, default: int = 2) -> int:
    """Remplace le formality_map codé en dur dans recommend.py."""
    return _occasion_formality().get(occasion, default)


def get_color_pairs_count() -> int:
    return len(_color_pairs())


def get_occasion_formality_dict() -> dict[str, int]:
    return dict(_occasion_formality())

