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
    clothing_sizes = ["xs", "s", "m", "l", "xl", "xxl"]

    rows: list[dict[str, int | float | str]] = []
    for _ in range(n_samples):
        age = rng.randint(16, 65)
        height_cm = rng.randint(150, 200)
        clothing_size = rng.choice(clothing_sizes)
        top_size = rng.choice(clothing_sizes)
        bottom_size = rng.choice(clothing_sizes)
        shoe_size = str(rng.randint(36, 46))
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
            "clothing_size": clothing_size,
            "top_size": top_size,
            "bottom_size": bottom_size,
            "shoe_size": shoe_size,
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


def real_training_pairs_from_feedback(
    catalog: list[OutfitItem],
    feedback_log_path: Path,
) -> pd.DataFrame:
    if not feedback_log_path.exists():
        return pd.DataFrame()

    catalog_map = {item.id: item for item in catalog}

    events: list[dict] = []
    with feedback_log_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                events.append(row)

    if not events:
        return pd.DataFrame()

    events_df = pd.DataFrame(events)
    required_cols = {
        "session_id",
        "user_id",
        "outfit_id",
        "event_type",
        "gender",
        "age",
        "height_cm",
        "body_shape",
        "style_preferences",
        "dominant_occasion",
        "weather_bucket",
    }
    if not required_cols.issubset(set(events_df.columns)):
        return pd.DataFrame()

    rows: list[dict[str, int | float | str]] = []
    grouped = events_df.groupby("session_id", dropna=False)
    for session_id, session in grouped:
        selected_ids = set(
            str(v)
            for v in session.loc[session["event_type"].isin(["selected", "click"]), "outfit_id"].tolist()
        )
        impressions = session.loc[session["event_type"] == "impression"]

        for _, impression in impressions.iterrows():
            outfit_id = str(impression["outfit_id"])
            if outfit_id not in catalog_map:
                continue

            item = catalog_map[outfit_id]

            pref_raw = impression.get("style_preferences", [])
            if isinstance(pref_raw, str):
                pref_styles = [value.strip().lower() for value in pref_raw.split(",") if value.strip()]
            elif isinstance(pref_raw, list):
                pref_styles = [str(value).strip().lower() for value in pref_raw]
            else:
                pref_styles = []

            gender = str(impression.get("gender", "unknown"))
            clothing_size = str(impression.get("clothing_size", "unknown")).lower()
            top_size = str(impression.get("top_size", "unknown")).lower()
            bottom_size = str(impression.get("bottom_size", "unknown")).lower()
            shoe_size = str(impression.get("shoe_size", "unknown")).lower()
            body_shape = str(impression.get("body_shape", "unknown"))
            occasion = str(impression.get("dominant_occasion", "casual"))
            weather = str(impression.get("weather_bucket", "mild"))

            style_match = int(any(style in item.styles for style in pref_styles))
            occasion_match = int(occasion in item.occasions)
            weather_match = int(weather in item.weather)
            shape_match = int(body_shape in item.body_shapes or body_shape == "unknown")
            gender_match = int(gender in item.genders or "unisex" in item.genders)

            row: dict[str, int | float | str] = {
                "session_id": str(session_id),
                "event_ts": str(impression.get("timestamp", "")),
                "age": int(impression.get("age", 30)),
                "height_cm": int(impression.get("height_cm", 170)),
                "clothing_size": clothing_size,
                "top_size": top_size,
                "bottom_size": bottom_size,
                "shoe_size": shoe_size,
                "gender": gender,
                "body_shape": body_shape,
                "occasion": occasion,
                "weather": weather,
                "outfit_id": outfit_id,
                "style_match": style_match,
                "occasion_match": occasion_match,
                "weather_match": weather_match,
                "shape_match": shape_match,
                "gender_match": gender_match,
                "label": int(outfit_id in selected_ids),
            }

            for style in KNOWN_STYLES:
                row[f"pref_{style}"] = int(style in pref_styles)
                row[f"outfit_style_{style}"] = int(style in item.styles)

            rows.append(row)

    return pd.DataFrame(rows)
