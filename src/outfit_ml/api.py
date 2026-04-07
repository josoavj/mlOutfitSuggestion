from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from .context import (
    AppIntegrationError,
    OpenWeatherError,
    agenda_to_labels,
    fetch_openweather,
    fetch_today_agenda_entries,
    fetch_user_profile,
)
from .recommend import OutfitRecommender
from .schemas import (
    AutoRecommendationRequest,
    CameraRecommendationRequest,
    CameraRecommendationResponse,
    ContextRecommendationRequest,
    FaceEnrollRequest,
    FaceEnrollResponse,
    FaceIdentifyRequest,
    FaceIdentifyResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from .vision import FaceRegistry, VisionError, VisionUnavailableError


load_dotenv()


app = FastAPI(title="Outfit Suggestion API", version="0.1.0")


@lru_cache
def get_recommender() -> OutfitRecommender:
    return OutfitRecommender()


@lru_cache
def get_face_registry() -> FaceRegistry:
    return FaceRegistry()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest) -> RecommendationResponse:
    try:
        recommender = get_recommender()
        return recommender.recommend(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Modele absent. Lance d'abord l'entrainement.",
        ) from exc


@app.post("/recommend/context", response_model=RecommendationResponse)
def recommend_from_context(request: ContextRecommendationRequest) -> RecommendationResponse:
    try:
        weather = fetch_openweather(request.location)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    base_request = RecommendationRequest(
        user_id=request.user_id,
        gender=request.gender,
        age=request.age,
        height_cm=request.height_cm,
        style_preferences=request.style_preferences,
        body_shape=request.body_shape,
        body_measurements=request.body_measurements,
        agenda=agenda_to_labels(request.agenda_entries),
        location=request.location,
        weather=weather,
        top_k=request.top_k,
    )
    return recommend(base_request)


@app.post("/recommend/auto", response_model=RecommendationResponse)
def recommend_auto(request: AutoRecommendationRequest) -> RecommendationResponse:
    try:
        profile = fetch_user_profile(request.user_id)
        agenda_entries = fetch_today_agenda_entries(request.user_id)
    except AppIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved_location = (request.location or profile.location or "").strip()
    if not resolved_location:
        raise HTTPException(
            status_code=400,
            detail="Location absente: fournir request.location ou location dans le profil.",
        )

    try:
        weather = fetch_openweather(resolved_location)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    base_request = RecommendationRequest(
        user_id=profile.user_id,
        gender=profile.gender,
        age=profile.age,
        height_cm=profile.height_cm,
        style_preferences=profile.style_preferences,
        body_shape=profile.body_shape,
        body_measurements=profile.body_measurements,
        agenda=agenda_to_labels(agenda_entries),
        location=resolved_location,
        weather=weather,
        top_k=request.top_k,
    )
    return recommend(base_request)


@app.post("/vision/enroll", response_model=FaceEnrollResponse)
def vision_enroll(request: FaceEnrollRequest) -> FaceEnrollResponse:
    try:
        registry = get_face_registry()
        registry.enroll(request.user_id, request.image_base64)
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except VisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FaceEnrollResponse(user_id=request.user_id, status="enrolled")


@app.post("/vision/identify", response_model=FaceIdentifyResponse)
def vision_identify(request: FaceIdentifyRequest) -> FaceIdentifyResponse:
    try:
        registry = get_face_registry()
        matches = registry.identify(
            request.image_base64,
            threshold=request.threshold,
            max_results=request.max_results,
        )
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except VisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FaceIdentifyResponse(matches=matches)


@app.post("/mirror/recommend-from-camera", response_model=CameraRecommendationResponse)
def recommend_from_camera(request: CameraRecommendationRequest) -> CameraRecommendationResponse:
    try:
        registry = get_face_registry()
        matches = registry.identify(
            request.image_base64,
            threshold=request.threshold,
            max_results=1,
        )
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except VisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not matches:
        raise HTTPException(
            status_code=404,
            detail="Aucun utilisateur reconnu. Faire l'enrolement via /vision/enroll.",
        )

    best_match = matches[0]
    recommendation = recommend_auto(
        AutoRecommendationRequest(
            user_id=best_match.user_id,
            location=request.location,
            top_k=request.top_k,
        )
    )

    return CameraRecommendationResponse(
        matched_user_id=best_match.user_id,
        face_match=best_match,
        recommendation=recommendation,
    )
