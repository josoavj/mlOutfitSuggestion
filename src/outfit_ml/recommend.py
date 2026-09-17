from __future__ import annotations

from pathlib import Path
from typing import Callable

import joblib
import pandas as pd

from .dataset.data import OutfitItem, load_catalog
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
        from datetime import datetime
        from .wardrobe.store import wardrobe_store
        from .preferences.store import preferences_store
        from .composition.engine import compose_outfits
        from .composition.models import CompositionContext
        from .wardrobe.models import WardrobeItem, Category, Color, Pattern, Season

        inferred_shape = request.body_shape or infer_body_shape(request.body_measurements)
        occasion = dominant_occasion(request.agenda)
        weather = weather_bucket(request.weather.temperature_c, request.weather.condition)

        # 1. Determine CompositionContext
        formality_map = {
            "sport": 1,
            "casual": 2,
            "outdoor": 2,
            "work": 3,
            "date": 3,
            "meeting": 4,
            "event": 5
        }
        dom_formality = formality_map.get(occasion, 3)

        warmth_map = {
            "hot": 1,
            "mild": 3,
            "rainy": 3,
            "cold": 5
        }
        target_w = warmth_map.get(weather, 3)

        prefs = preferences_store.get(request.user_id)
        if prefs:
            if prefs.niveau_formalite_prefere is not None:
                dom_formality = int((dom_formality + prefs.niveau_formalite_prefere) / 2)
            if prefs.tolerance_meteo == "frileux":
                target_w = min(5, target_w + 1)
            elif prefs.tolerance_meteo == "resistant":
                target_w = max(1, target_w - 1)

        context = CompositionContext(
            weather_bucket=weather,
            target_warmth=target_w,
            dominant_occasion_formality=dom_formality,
            formality_tolerance=1,
            user_id=request.user_id,
            gender=request.gender,
            age=request.age,
            height_cm=request.height_cm,
            body_shape=inferred_shape,
            occasion=occasion,
        )

        # 2. Get user items or bootstrap if incomplete
        user_items = wardrobe_store.list_items(request.user_id)
        
        has_top = any(i.category.value == "top" or i.category.value == "dress" for i in user_items)
        has_bottom = any(i.category.value == "bottom" or i.category.value == "dress" for i in user_items)
        has_shoes = any(i.category.value == "shoes" for i in user_items)

        if not (has_top and has_bottom and has_shoes):
            # La garde-robe est incomplète, on génère des items de complément variés
            bootstrap_items = []
            categories = [Category.top, Category.bottom, Category.shoes, Category.outerwear]
            
            # Pools variés pour éviter la répétition structurelle
            sub_pools = {
                Category.top: ["chemise", "t_shirt", "pull", "sweat", "polo", "debardeur"],
                Category.bottom: ["pantalon", "jean", "short", "jupe", "chino"],
                Category.shoes: ["baskets", "mocassins", "bottines", "chaussures_habillees", "sandales"],
                Category.outerwear: ["veste", "manteau", "blazer", "doudoune", "trench"]
            }
            
            from .wardrobe.models import Material, ItemGender
            materials = [Material.coton, Material.denim, Material.laine, Material.synthetique]
            colors = [Color.noir, Color.blanc, Color.bleu_marine, Color.beige, Color.gris, Color.marron]
            genders = [ItemGender.masculin, ItemGender.feminin, ItemGender.unisex]
            
            idx = 0
            for f in range(1, 6):
                for w in range(1, 6):
                    for cat in categories:
                        pool = sub_pools[cat]
                        sub = pool[idx % len(pool)]
                        col = colors[idx % len(colors)]
                        mat = materials[idx % len(materials)]
                        gen = genders[idx % len(genders)]
                        
                        bootstrap_items.append(
                            WardrobeItem(
                                item_id=f"boot_{cat.value}_{f}_{w}_{idx}",
                                user_id=request.user_id,
                                category=cat,
                                subcategory=sub,
                                color_primary=col,
                                material=mat,
                                gender=gen,
                                formality_levels=[f], # Simple pour le bootstrap initial
                                warmth_ratings=[w],
                                pattern=Pattern.uni,
                                season_suitability=[Season.printemps, Season.ete, Season.automne, Season.hiver]
                            )
                        )
                        idx += 1
            # On mélange les items réels et les items bootstrap
            user_items = user_items + bootstrap_items

        # 3. Filter out banned items
        if prefs and prefs.items_bannis:
            user_items = [item for item in user_items if item.item_id not in prefs.items_bannis]

        # 4. Compose outfits
        combinations = compose_outfits(
            items=user_items,
            context=context,
            top_k=request.top_k
        )

        # 5. Mark suggested items
        suggested_ids = [item.item_id for c in combinations for item in c.items]
        if suggested_ids:
            wardrobe_store.mark_suggested(request.user_id, suggested_ids)

        # 6. Map to OutfitSuggestion
        suggestions: list[OutfitSuggestion] = []
        for i, comb in enumerate(combinations):
            item_descs = [f"{item.subcategory} ({item.color_primary.value})" for item in comb.items]
            reasons = ["Bonne compatibilité globale et harmonie des couleurs"]
            if weather in ["cold", "hot"]:
                reasons.append("Adapté à la météo du jour")
            if occasion != "casual":
                reasons.append(f"Cohérent avec une occasion de type {occasion}")
            if prefs and prefs.styles_aimes:
                reasons.append("Correspond à vos préférences de style")

            suggestions.append(
                OutfitSuggestion(
                    outfit_id=f"comb_{request.user_id}_{i}_{int(datetime.utcnow().timestamp())}",
                    outfit_label=f"Tenue composée de {', '.join([item.subcategory for item in comb.items])}",
                    outfit_items=item_descs,
                    score=float(round(comb.final_score, 4)),
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
