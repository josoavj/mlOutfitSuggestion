from __future__ import annotations

from pathlib import Path
from typing import Callable

import joblib
import pandas as pd

from .data import OutfitItem, load_catalog
from .features import (
    classify_agenda_text,
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
        self._catalog_cache = self._build_catalog_cache(self.catalog)

    @staticmethod
    def _build_catalog_cache(catalog: list[OutfitItem]) -> list[dict]:
        cached: list[dict] = []
        for item in catalog:
            styles = {style.lower() for style in item.styles}
            cached.append(
                {
                    "item": item,
                    "styles": styles,
                    "occasions": set(item.occasions),
                    "weather": set(item.weather),
                    "genders": set(item.genders),
                    "body_shapes": set(item.body_shapes),
                    "pref_clothing": preferred_size_for_item(item.id, "clothing"),
                    "pref_top": preferred_size_for_item(item.id, "top"),
                    "pref_bottom": preferred_size_for_item(item.id, "bottom"),
                    "pref_shoe_bucket": preferred_shoe_bucket_for_item(item.id),
                    "outfit_style_classic": int("classic" in styles),
                    "outfit_style_minimalist": int("minimalist" in styles),
                    "outfit_style_casual": int("casual" in styles),
                    "outfit_style_sport": int("sport" in styles),
                    "outfit_style_elegant": int("elegant" in styles),
                    "outfit_style_practical": int("practical" in styles),
                }
            )
        return cached

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
        pref_flags: dict[str, int],
        pref_style_set: set[str],
        normalized_sizes: tuple[str, str, str, str],
        cache_row: dict,
    ) -> dict[str, int | str]:
        item: OutfitItem = cache_row["item"]
        clothing_size, top_size, bottom_size, shoe_bucket = normalized_sizes

        row: dict[str, int | str] = {
            "age": request.age,
            "height_cm": request.height_cm,
            "gender": request.gender,
            "body_shape": inferred_shape,
            "occasion": occasion,
            "weather": weather,
            "clothing_size": clothing_size,
            "top_size": top_size,
            "bottom_size": bottom_size,
            "shoe_bucket": shoe_bucket,
            "outfit_id": item.id,
            "style_match": int(any(style in cache_row["styles"] for style in pref_style_set)),
            "occasion_match": int(occasion in cache_row["occasions"]),
            "weather_match": int(weather in cache_row["weather"]),
            "shape_match": int(inferred_shape in cache_row["body_shapes"] or inferred_shape == "unknown"),
            "gender_match": int(request.gender in cache_row["genders"] or "unisex" in cache_row["genders"]),
            "clothing_size_match": int(clothing_size == cache_row["pref_clothing"]),
            "top_size_match": int(top_size == cache_row["pref_top"]),
            "bottom_size_match": int(bottom_size == cache_row["pref_bottom"]),
            "shoe_size_match": int(shoe_bucket == cache_row["pref_shoe_bucket"]),
            **pref_flags,
            "outfit_style_classic": cache_row["outfit_style_classic"],
            "outfit_style_minimalist": cache_row["outfit_style_minimalist"],
            "outfit_style_casual": cache_row["outfit_style_casual"],
            "outfit_style_sport": cache_row["outfit_style_sport"],
            "outfit_style_elegant": cache_row["outfit_style_elegant"],
            "outfit_style_practical": cache_row["outfit_style_practical"],
        }

        return row

    @staticmethod
    def _agenda_labels(agenda: list[str]) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()
        for entry in agenda:
            label = classify_agenda_text(str(entry))
            primary = label.split(" - ", 1)[0].strip().lower()
            if primary and primary not in seen:
                labels.append(primary)
                seen.add(primary)
        return labels

    @staticmethod
    def _select_best(
        ranked: list[tuple[OutfitItem, float]],
        selected_ids: set[str],
        predicate: Callable[[OutfitItem], bool],
    ) -> tuple[OutfitItem, float] | None:
        for item, score in ranked:
            if item.id in selected_ids:
                continue
            if predicate(item):
                selected_ids.add(item.id)
                return item, score
        return None

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        inferred_shape = request.body_shape or infer_body_shape(request.body_measurements)
        occasion = dominant_occasion(request.agenda)
        weather = weather_bucket(request.weather.temperature_c, request.weather.condition)
        agenda_labels = self._agenda_labels(request.agenda)
        pref_flags = encode_style_flags(request.style_preferences)
        pref_style_set = {style.strip().lower() for style in request.style_preferences}
        normalized_sizes = (
            normalize_size(request.clothing_size),
            normalize_size(request.top_size),
            normalize_size(request.bottom_size),
            shoe_size_bucket(request.shoe_size),
        )

        rows: list[dict[str, int | str]] = []
        for cache_row in self._catalog_cache:
            rows.append(
                self._row_for_item(
                    request,
                    inferred_shape,
                    occasion,
                    weather,
                    pref_flags,
                    pref_style_set,
                    normalized_sizes,
                    cache_row,
                )
            )

        features_df = pd.DataFrame(rows)
        scores = self.model.predict_proba(features_df)[:, 1]

        ranked = sorted(
            zip(self.catalog, scores, strict=True),
            key=lambda pair: pair[1],
            reverse=True,
        )

        selected: list[tuple[OutfitItem, float]] = []
        selected_ids: set[str] = set()
        for label in agenda_labels:
            if len(selected) >= request.top_k:
                break
            match_both = self._select_best(
                ranked,
                selected_ids,
                lambda item, lbl=label: lbl in item.occasions and weather in item.weather,
            )
            if match_both:
                selected.append(match_both)
                continue
            match_label = self._select_best(
                ranked,
                selected_ids,
                lambda item, lbl=label: lbl in item.occasions,
            )
            if match_label:
                selected.append(match_label)

        if len(selected) < request.top_k and weather:
            has_weather = any(weather in item.weather for item, _ in selected)
            if not has_weather:
                weather_pick = self._select_best(
                    ranked,
                    selected_ids,
                    lambda item: weather in item.weather,
                )
                if weather_pick:
                    selected.append(weather_pick)

        for item, score in ranked:
            if len(selected) >= request.top_k:
                break
            if item.id in selected_ids:
                continue
            selected_ids.add(item.id)
            selected.append((item, score))

        suggestions: list[OutfitSuggestion] = []
        for item, score in selected:
            reasons = []
            if any(style in item.styles for style in request.style_preferences):
                reasons.append("Correspond aux préférences de style")
            if weather in item.weather:
                reasons.append("Adapté à la météo")
            agenda_matches = [label for label in agenda_labels if label in item.occasions]
            if agenda_matches:
                reasons.append("Cohérent avec l'agenda: " + ", ".join(agenda_matches))
            if not reasons:
                reasons.append("Bonne compatibilité globale")

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
