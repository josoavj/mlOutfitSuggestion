from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import Random

import pandas as pd

from .features import (
    KNOWN_OCCASIONS,
    KNOWN_SHOE_BUCKETS,
    KNOWN_SIZES,
    KNOWN_STYLES,
    KNOWN_WEATHER,
    preferred_shoe_bucket_for_item,
    preferred_size_for_item,
)


@dataclass
class OutfitItem:
    id: str
    label: str
    items: list[str]
    items_by_gender: dict[str, list[str]]
    styles: list[str]
    occasions: list[str]
    weather: list[str]
    genders: list[str]
    body_shapes: list[str]


def load_catalog(path: Path) -> list[OutfitItem]:
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    catalog: list[OutfitItem] = []
    for row in raw:
        catalog.append(
            OutfitItem(
                id=row["id"],
                label=row["label"],
                items=[str(value) for value in row.get("items", [])],
                items_by_gender={
                    str(key): [str(value) for value in values]
                    for key, values in dict(row.get("items_by_gender", {})).items()
                    if isinstance(values, list)
                },
                styles=row["styles"],
                occasions=row["occasions"],
                weather=row["weather"],
                genders=row["genders"],
                body_shapes=row["body_shapes"],
            )
        )
    return catalog


def synthetic_training_pairs(catalog: list[OutfitItem], n_samples: int, seed: int = 42) -> pd.DataFrame:
    rng = Random(seed)
    body_shapes = ["hourglass", "rectangle", "pear", "inverted_triangle", "oval"]
    genders = ["female", "male", "non_binary"]

    rows: list[dict[str, int | float | str]] = []
    for _ in range(n_samples):
        age = rng.randint(16, 65)
        height_cm = rng.randint(150, 200)
        gender = rng.choice(genders)
        body_shape = rng.choice(body_shapes)
        occasion = rng.choice(KNOWN_OCCASIONS)
        weather = rng.choice(KNOWN_WEATHER)
        clothing_size = rng.choice(KNOWN_SIZES[:-1])
        top_size = rng.choice(KNOWN_SIZES[:-1])
        bottom_size = rng.choice(KNOWN_SIZES[:-1])
        shoe_bucket = rng.choice(KNOWN_SHOE_BUCKETS[:-1])

        pref_styles = rng.sample(KNOWN_STYLES, k=rng.randint(1, 2))

        item = rng.choice(catalog)

        style_match = int(any(style in item.styles for style in pref_styles))
        occasion_match = int(occasion in item.occasions)
        weather_match = int(weather in item.weather)
        shape_match = int(body_shape in item.body_shapes)
        gender_match = int(gender in item.genders or "unisex" in item.genders)
        clothing_size_match = int(clothing_size == preferred_size_for_item(item.id, "clothing"))
        top_size_match = int(top_size == preferred_size_for_item(item.id, "top"))
        bottom_size_match = int(bottom_size == preferred_size_for_item(item.id, "bottom"))
        shoe_size_match = int(shoe_bucket == preferred_shoe_bucket_for_item(item.id))

        signal = (
            0.35 * style_match
            + 0.25 * occasion_match
            + 0.20 * weather_match
            + 0.10 * shape_match
            + 0.10 * gender_match
            + 0.04 * clothing_size_match
            + 0.03 * top_size_match
            + 0.03 * bottom_size_match
            + 0.03 * shoe_size_match
        )
        noisy_threshold = 0.55 + rng.uniform(-0.08, 0.08)
        label = int(signal >= noisy_threshold)

        row: dict[str, int | float | str] = {
            "age": age,
            "height_cm": height_cm,
            "gender": gender,
            "body_shape": body_shape,
            "occasion": occasion,
            "weather": weather,
            "clothing_size": clothing_size,
            "top_size": top_size,
            "bottom_size": bottom_size,
            "shoe_bucket": shoe_bucket,
            "outfit_id": item.id,
            "style_match": style_match,
            "occasion_match": occasion_match,
            "weather_match": weather_match,
            "shape_match": shape_match,
            "gender_match": gender_match,
            "clothing_size_match": clothing_size_match,
            "top_size_match": top_size_match,
            "bottom_size_match": bottom_size_match,
            "shoe_size_match": shoe_size_match,
            "label": label,
        }

        for style in KNOWN_STYLES:
            row[f"pref_{style}"] = int(style in pref_styles)
            row[f"outfit_style_{style}"] = int(style in item.styles)

        rows.append(row)

    return pd.DataFrame(rows)
