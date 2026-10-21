"""Génère les combinaisons candidates à partir des items ayant passé les
filtres durs (étape 1), puis les filtre par compatibilité (étape 2).

Une tenue = soit (top + bottom), soit (dress), + shoes obligatoires,
+ au plus 1 outerwear optionnel, + au plus 1 accessory optionnel.
Pour rester praticable, le nombre de candidats est plafonné via
max_candidates plutôt que d'énumérer l'intégralité du produit cartésien
sur de grandes garde-robes.
"""

from __future__ import annotations

import random
from itertools import product
from typing import Generator, Sequence, TypeVar

from ..wardrobe.models import Category, WardrobeItem
from .compatibility import combination_compatibility_score
from .models import OutfitCombination

T = TypeVar("T")


def _by_category(items: list[WardrobeItem], category: Category) -> list[WardrobeItem]:
    return [i for i in items if i.category == category]


def _sample_product(
    bases: Sequence[list[WardrobeItem]],
    shoes: Sequence[WardrobeItem],
    outers: Sequence[WardrobeItem | None],
    accs: Sequence[WardrobeItem | None],
    rng: random.Random,
    num_samples: int,
) -> Generator[tuple[list[WardrobeItem], WardrobeItem, WardrobeItem | None, WardrobeItem | None], None, None]:
    """Échantillonnage aléatoire uniforme sans biais lexicographique."""
    for _ in range(num_samples):
        yield rng.choice(bases), rng.choice(shoes), rng.choice(outers), rng.choice(accs)


def generate_candidates(
    items: list[WardrobeItem],
    max_candidates: int = 500,
    rng: random.Random | None = None,
) -> list[OutfitCombination]:
    rng = rng or random.Random()

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

    if not base_sets or not shoes:
        return []

    total_possible = len(base_sets) * len(shoes) * len(outerwear) * len(accessories)

    if total_possible <= max_candidates * 3:
        combos = list(product(base_sets, shoes, outerwear, accessories))
        rng.shuffle(combos)
        combo_iter = combos
    else:
        combo_iter = _sample_product(base_sets, shoes, outerwear, accessories, rng, max_candidates * 4)

    candidates: list[OutfitCombination] = []
    seen_keys: set[tuple[str, ...]] = set()

    for base, shoe, outer, accessory in combo_iter:
        pieces = [*base, shoe]
        if outer:
            pieces.append(outer)
        if accessory:
            pieces.append(accessory)

        item_ids = tuple(sorted(p.item_id for p in pieces))
        if item_ids in seen_keys:
            continue
        seen_keys.add(item_ids)

        score = combination_compatibility_score(pieces)
        if score <= 0.0:
            continue

        candidates.append(OutfitCombination(items=pieces, compatibility_score=score))
        if len(candidates) >= max_candidates:
            break

    return candidates
