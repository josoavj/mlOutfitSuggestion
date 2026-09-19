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

        # 4. Compose outfits with ML Scoring
        from .composition.scoring import ml_combination_score
        combinations = compose_outfits(
            items=user_items,
            context=context,
            top_k=request.top_k,
            score_fn=ml_combination_score
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
                    outfit_id=f"comb_{request.user_id}_{i}_{int(datetime.now().timestamp())}",
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
