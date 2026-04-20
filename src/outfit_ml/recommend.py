from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from .data import OutfitItem, load_catalog
from .features import (
    dominant_occasion,
    encode_style_flags,
    infer_body_shape,
    normalize_size,
    preferred_shoe_bucket_for_item,
    preferred_size_for_item,
    shoe_size_bucket,
    weather_bucket,
)
from .schemas import OutfitSuggestion, RecommendationRequest, RecommendationResponse


class OutfitRecommender:
    def __init__(
        self,
        model_path: Path = Path("models/outfit_ranker.joblib"),
        catalog_path: Path = Path("configs/outfit_catalog.json"),
    ) -> None:
        self.model = joblib.load(model_path)
        self.catalog: list[OutfitItem] = load_catalog(catalog_path)

    @staticmethod
    def _items_for_gender(item: OutfitItem, gender: str) -> list[str]:
        normalized_gender = str(gender or "").strip().lower()
        if normalized_gender in item.items_by_gender and item.items_by_gender[normalized_gender]:
            return item.items_by_gender[normalized_gender]
        if "unisex" in item.items_by_gender and item.items_by_gender["unisex"]:
            return item.items_by_gender["unisex"]
        return item.items

    def _row_for_item(
        self,
        request: RecommendationRequest,
        inferred_shape: str,
        occasion: str,
        weather: str,
        item: OutfitItem,
    ) -> dict[str, int | str]:
        pref_flags = encode_style_flags(request.style_preferences)

        row: dict[str, int | str] = {
            "age": request.age,
            "height_cm": request.height_cm,
            "clothing_size": request.clothing_size,
            "top_size": request.top_size,
            "bottom_size": request.bottom_size,
            "shoe_size": request.shoe_size,
            "gender": request.gender,
            "body_shape": inferred_shape,
            "occasion": occasion,
            "weather": weather,
            "clothing_size": normalize_size(request.clothing_size),
            "top_size": normalize_size(request.top_size),
            "bottom_size": normalize_size(request.bottom_size),
            "shoe_bucket": shoe_size_bucket(request.shoe_size),
            "outfit_id": item.id,
            "style_match": int(any(s in item.styles for s in request.style_preferences)),
            "occasion_match": int(occasion in item.occasions),
            "weather_match": int(weather in item.weather),
            "shape_match": int(inferred_shape in item.body_shapes or inferred_shape == "unknown"),
            "gender_match": int(request.gender in item.genders or "unisex" in item.genders),
            "clothing_size_match": int(
                normalize_size(request.clothing_size) == preferred_size_for_item(item.id, "clothing")
            ),
            "top_size_match": int(
                normalize_size(request.top_size) == preferred_size_for_item(item.id, "top")
            ),
            "bottom_size_match": int(
                normalize_size(request.bottom_size) == preferred_size_for_item(item.id, "bottom")
            ),
            "shoe_size_match": int(
                shoe_size_bucket(request.shoe_size) == preferred_shoe_bucket_for_item(item.id)
            ),
            **pref_flags,
        }

        styles = {style.lower() for style in item.styles}
        row["outfit_style_classic"] = int("classic" in styles)
        row["outfit_style_minimalist"] = int("minimalist" in styles)
        row["outfit_style_casual"] = int("casual" in styles)
        row["outfit_style_sport"] = int("sport" in styles)
        row["outfit_style_elegant"] = int("elegant" in styles)
        row["outfit_style_practical"] = int("practical" in styles)

        return row

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        inferred_shape = request.body_shape or infer_body_shape(request.body_measurements)
        occasion = dominant_occasion(request.agenda)
        weather = weather_bucket(request.weather.temperature_c, request.weather.condition)

        rows: list[dict[str, int | str]] = []
        for item in self.catalog:
            rows.append(self._row_for_item(request, inferred_shape, occasion, weather, item))

        features_df = pd.DataFrame(rows)
        scores = self.model.predict_proba(features_df)[:, 1]

        ranked = sorted(
            zip(self.catalog, scores, strict=True),
            key=lambda pair: pair[1],
            reverse=True,
        )

        suggestions: list[OutfitSuggestion] = []
        for item, score in ranked[: request.top_k]:
            reasons = []
            if any(style in item.styles for style in request.style_preferences):
                reasons.append("correspond aux préférences de style")
            if weather in item.weather:
                reasons.append("adapté à la météo")
            if occasion in item.occasions:
                reasons.append("cohérent avec l'agenda")
            if not reasons:
                reasons.append("bonne compatibilité globale")

            suggestions.append(
                OutfitSuggestion(
                    outfit_id=item.id,
                    outfit_label=item.label,
                    outfit_items=self._items_for_gender(item, request.gender),
                    score=float(round(score, 4)),
                    reasons=reasons,
                )
            )

        return RecommendationResponse(
            user_id=request.user_id,
            inferred_body_shape=inferred_shape,
            dominant_occasion=occasion,
            weather_bucket=weather,
            suggestions=suggestions,
        )
