from __future__ import annotations

from pathlib import Path
import joblib

from .features import (
    dominant_occasion,
    infer_body_shape,
    weather_bucket,
)
from .schemas import OutfitSuggestion, RecommendationRequest, RecommendationResponse


class OutfitRecommender:
    def __init__(
        self,
        model_path: Path = Path("models/outfit_ranker.joblib"),
    ) -> None:
        self.model = joblib.load(model_path)

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
        from .composition.ontology_rules import min_formality_for_occasion
        dom_formality = min_formality_for_occasion(occasion.capitalize(), default=3)

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

        # 2. Get user items or bootstrap only MISSING categories
        user_items = wardrobe_store.list_items(request.user_id)

        has_top = any(i.category.value == "top" or i.category.value == "dress" for i in user_items)
        has_bottom = any(i.category.value == "bottom" or i.category.value == "dress" for i in user_items)
        has_shoes = any(i.category.value == "shoes" for i in user_items)

        missing_categories: list[Category] = []
        if not has_top:
            missing_categories.append(Category.top)
        if not has_bottom and not any(i.category.value == "dress" for i in user_items):
            missing_categories.append(Category.bottom)
        if not has_shoes:
            missing_categories.append(Category.shoes)

        if missing_categories:
            from .wardrobe.models import Material, ItemGender
            bootstrap_items = []

            templates = {
                Category.top: [
                    ("chemise", Color.blanc, Material.coton, [3, 4], [2, 3]),
                    ("t_shirt", Color.noir, Material.coton, [1, 2], [1, 2]),
                    ("pull", Color.bleu_marine, Material.laine, [2, 3], [4, 5]),
                    ("polo", Color.gris, Material.coton, [2, 3], [2, 3]),
                    ("sweat", Color.beige, Material.coton, [1, 2], [3, 4]),
                ],
                Category.bottom: [
                    ("pantalon", Color.noir, Material.coton, [3, 4], [2, 3]),
                    ("jean", Color.bleu_marine, Material.denim, [2, 3], [2, 3, 4]),
                    ("chino", Color.beige, Material.coton, [3, 4], [2, 3]),
                    ("short", Color.gris, Material.coton, [1, 2], [1, 2]),
                ],
                Category.shoes: [
                    ("baskets", Color.blanc, Material.synthetique, [1, 2, 3], [2, 3]),
                    ("mocassins", Color.marron, Material.cuir, [3, 4, 5], [2, 3]),
                    ("bottines", Color.noir, Material.cuir, [3, 4], [4, 5]),
                    ("sandales", Color.beige, Material.cuir, [1, 2], [1, 2]),
                ],
                Category.outerwear: [
                    ("veste", Color.bleu_marine, Material.coton, [3, 4], [3, 4]),
                    ("manteau", Color.noir, Material.laine, [4, 5], [4, 5]),
                ]
            }

            idx = 0
            for cat in missing_categories:
                cat_templates = templates.get(cat, [])
                for sub, col, mat, f_levels, w_ratings in cat_templates:
                    bootstrap_items.append(
                        WardrobeItem(
                            item_id=f"boot_{cat.value}_{idx}",
                            user_id=request.user_id,
                            category=cat,
                            subcategory=sub,
                            color_primary=col,
                            material=mat,
                            gender=ItemGender.unisex,
                            formality_levels=f_levels,
                            warmth_ratings=w_ratings,
                            pattern=Pattern.uni,
                            season_suitability=[Season.printemps, Season.ete, Season.automne, Season.hiver]
                        )
                    )
                    idx += 1

            user_items = user_items + bootstrap_items

        # 3. Filter out banned items
        if prefs and prefs.items_bannis:
            user_items = [item for item in user_items if item.item_id not in prefs.items_bannis]

        # 4. Compose outfits with ML Scoring
        import time
        import uuid
        from .monitoring import log_inference
        from .composition.scoring import ml_combination_score

        t0 = time.perf_counter()
        stats: dict = {}

        combinations = compose_outfits(
            items=user_items,
            context=context,
            top_k=request.top_k,
            score_fn=ml_combination_score,
            stats=stats,
        )

        # 5. Mark suggested items
        suggested_ids = [item.item_id for c in combinations for item in c.items if not item.item_id.startswith("boot_")]
        if suggested_ids:
            wardrobe_store.mark_suggested(request.user_id, suggested_ids)

        # 6. Map to OutfitSuggestion
        suggestions: list[OutfitSuggestion] = []
        user_styles = set(request.style_preferences or (prefs.styles_aimes if prefs else []))

        for comb in combinations:
            item_descs = [f"{item.subcategory} ({item.color_primary.value})" for item in comb.items]
            reasons = ["Bonne compatibilité globale et harmonie des couleurs"]

            if weather in ["cold", "hot"]:
                reasons.append("Adapté à la météo du jour")
            if occasion != "casual":
                reasons.append(f"Cohérent avec une occasion de type {occasion}")
            if user_styles:
                reasons.append("Correspond à vos préférences de style")

            outfit_hash = "-".join(sorted(item.item_id for item in comb.items))
            suggestions.append(
                OutfitSuggestion(
                    outfit_id=f"outfit_{outfit_hash}",
                    outfit_label=f"Tenue composée de {', '.join([item.subcategory for item in comb.items])}",
                    outfit_items=item_descs,
                    score=float(round(comb.final_score, 4)),
                    reasons=reasons,
                )
            )

        log_inference(
            request_id=uuid.uuid4().hex,
            user_id=request.user_id,
            n_candidates=stats.get("n_candidates", 0),
            n_suggestions=len(suggestions),
            score_summary=stats,
            ml_fallbacks=stats.get("ml_fallbacks", 0),
            latency_ms=(time.perf_counter() - t0) * 1000,
            outfit_keys=[" | ".join(sorted(s.outfit_items)) for s in suggestions],
            top_keys=[s.outfit_items[0] for s in suggestions if s.outfit_items],
        )

        return RecommendationResponse(
            user_id=request.user_id,
            inferred_body_shape=inferred_shape,
            dominant_occasion=occasion,
            weather_bucket=weather,
            suggestions=suggestions,
        )
