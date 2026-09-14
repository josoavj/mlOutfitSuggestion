"""Génère les combinaisons candidates à partir des items ayant passé les
filtres durs (étape 1), puis les filtre par compatibilité (étape 2).

Une tenue = soit (top + bottom), soit (dress), + shoes obligatoires,
+ au plus 1 outerwear optionnel, + au plus 1 accessory optionnel.
Pour rester praticable, le nombre de candidats est plafonné via
max_candidates plutôt que d'énumérer l'intégralité du produit cartésien
sur de grandes garde-robes.
"""

from __future__ import annotations

from itertools import product

from ..wardrobe.models import Category, WardrobeItem
from .compatibility import combination_compatibility_score
from .models import OutfitCombination


def _by_category(items: list[WardrobeItem], category: Category) -> list[WardrobeItem]:
    return [i for i in items if i.category == category]


def generate_candidates(items: list[WardrobeItem], max_candidates: int = 500) -> list[OutfitCombination]:
    tops = _by_category(items, Category.top)
    bottoms = _by_category(items, Category.bottom)
    dresses = _by_category(items, Category.dress)
    shoes = _by_category(items, Category.shoes)
    outerwear: list[WardrobeItem | None] = [None] + _by_category(items, Category.outerwear)
    accessories: list[WardrobeItem | None] = [None] + _by_category(items, Category.accessory)

    base_sets: list[list[WardrobeItem]] = []
    for top, bottom in product(tops, bottoms):
        base_sets.append([top, bottom])
    for dress in dresses:
        base_sets.append([dress])

    candidates: list[OutfitCombination] = []
    for base, shoe, outer, accessory in product(base_sets, shoes, outerwear, accessories):
        pieces = [*base, shoe]
        if outer:
            pieces.append(outer)
        if accessory:
            pieces.append(accessory)

        score = combination_compatibility_score(pieces)
        if score <= 0.0:
            continue

        candidates.append(OutfitCombination(items=pieces, compatibility_score=score))
        if len(candidates) >= max_candidates:
            return candidates

    return candidates
