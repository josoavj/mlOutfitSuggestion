from __future__ import annotations

import os
import json
from functools import lru_cache
from pathlib import Path
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .context import (
    AppIntegrationError,
    OpenWeatherError,
    agenda_to_labels,
    fetch_openweather,
    fetch_today_agenda_entries,
    fetch_user_profile,
)
from .feedback import append_feedback_event, append_feedback_events, feedback_stats
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
    FeedbackEventRequest,
    FeedbackEventResponse,
    FeedbackBatchRequest,
    FeedbackBatchResponse,
    FeedbackStatsResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from .vision import FaceRegistry, VisionError, VisionUnavailableError


load_dotenv()


def _allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


def _api_auth_enabled() -> bool:
    return os.getenv("API_AUTH_ENABLED", "false").strip().lower() == "true"


def _api_key() -> str:
    return os.getenv("API_AUTH_KEY", "").strip()


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not _api_auth_enabled():
        return

    key = _api_key()
    if not key:
        raise HTTPException(status_code=500, detail="API_AUTH_ENABLED=true mais API_AUTH_KEY manquante")

    if x_api_key != key:
        raise HTTPException(status_code=401, detail="Cle API invalide")


app = FastAPI(title="Outfit Suggestion API", version="0.1.0")

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
MODEL_METRICS_PATH = Path(__file__).resolve().parents[2] / "models" / "outfit_ranker_metrics.json"
if WEB_DIR.exists():
    app.mount("/ui-assets", StaticFiles(directory=str(WEB_DIR)), name="ui-assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_recommender() -> OutfitRecommender:
    return OutfitRecommender()


@lru_cache
def get_face_registry() -> FaceRegistry:
    return FaceRegistry()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _load_model_metrics() -> tuple[bool, dict]:
    if not MODEL_METRICS_PATH.exists():
        return False, {}

    try:
        content = MODEL_METRICS_PATH.read_text(encoding="utf-8")
        parsed = json.loads(content)
    except Exception:  # noqa: BLE001
        return True, {"error": "metrics_file_invalid"}

    if not isinstance(parsed, dict):
        return True, {"error": "metrics_format_invalid"}
    return True, parsed


@app.get("/ui")
def ui_page() -> FileResponse:
    if not WEB_DIR.exists():
        raise HTTPException(status_code=404, detail="UI non disponible")
    return FileResponse(WEB_DIR / "index.html")


@app.get("/dashboard/technical")
def technical_dashboard(_: None = Depends(require_api_key)) -> dict:
    model_present, model_metrics = _load_model_metrics()
    feedback = feedback_stats().model_dump()
    now_utc = datetime.now(UTC)
    metrics_modified_iso: str | None = None
    metrics_age_seconds: float | None = None
    if model_present:
        modified_ts = MODEL_METRICS_PATH.stat().st_mtime
        modified_dt = datetime.fromtimestamp(modified_ts, tz=UTC)
        metrics_modified_iso = modified_dt.isoformat()
        metrics_age_seconds = max(0.0, (now_utc - modified_dt).total_seconds())

    return {
        "service": {
            "status": "ok",
            "version": app.version,
            "server_time_utc": now_utc.isoformat(),
            "api_auth_enabled": _api_auth_enabled(),
            "data_source": os.getenv("MAGICMIRROR_DATA_SOURCE", "api").strip().lower(),
            "allowed_origins_count": len(_allowed_origins()),
        },
        "model": {
            "metrics_present": model_present,
            "metrics_path": str(MODEL_METRICS_PATH),
            "metrics_last_modified": MODEL_METRICS_PATH.stat().st_mtime if model_present else None,
            "metrics_last_modified_utc": metrics_modified_iso,
            "metrics_age_seconds": metrics_age_seconds,
            "metrics": model_metrics,
        },
        "feedback": feedback,
    }


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(
    request: RecommendationRequest,
    _: None = Depends(require_api_key),
) -> RecommendationResponse:
    try:
        recommender = get_recommender()
        return recommender.recommend(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Modele absent. Lance d'abord l'entrainement.",
        ) from exc


@app.post("/recommend/context", response_model=RecommendationResponse)
def recommend_from_context(
    request: ContextRecommendationRequest,
    _: None = Depends(require_api_key),
) -> RecommendationResponse:
    try:
        weather = fetch_openweather(request.location)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    base_request = RecommendationRequest(
        user_id=request.user_id,
        gender=request.gender,
        age=request.age,
        height_cm=request.height_cm,
        clothing_size=request.clothing_size,
        top_size=request.top_size,
        bottom_size=request.bottom_size,
        shoe_size=request.shoe_size,
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
def recommend_auto(
    request: AutoRecommendationRequest,
    _: None = Depends(require_api_key),
) -> RecommendationResponse:
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
        clothing_size=profile.clothing_size,
        top_size=profile.top_size,
        bottom_size=profile.bottom_size,
        shoe_size=profile.shoe_size,
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
def vision_enroll(
    request: FaceEnrollRequest,
    _: None = Depends(require_api_key),
) -> FaceEnrollResponse:
    try:
        registry = get_face_registry()
        registry.enroll(request.user_id, request.image_base64)
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except VisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FaceEnrollResponse(user_id=request.user_id, status="enrolled")


@app.post("/vision/identify", response_model=FaceIdentifyResponse)
def vision_identify(
    request: FaceIdentifyRequest,
    _: None = Depends(require_api_key),
) -> FaceIdentifyResponse:
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
def recommend_from_camera(
    request: CameraRecommendationRequest,
    _: None = Depends(require_api_key),
) -> CameraRecommendationResponse:
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


@app.post("/feedback/event", response_model=FeedbackEventResponse)
def create_feedback_event(
    request: FeedbackEventRequest,
    _: None = Depends(require_api_key),
) -> FeedbackEventResponse:
    event_id = append_feedback_event(request)
    return FeedbackEventResponse(status="ok", event_id=event_id)


@app.post("/feedback/events", response_model=FeedbackBatchResponse)
def create_feedback_events(
    request: FeedbackBatchRequest,
    _: None = Depends(require_api_key),
) -> FeedbackBatchResponse:
    event_ids = append_feedback_events(request.events)
    return FeedbackBatchResponse(
        status="ok",
        created_count=len(event_ids),
        event_ids=event_ids,
    )


@app.get("/feedback/stats", response_model=FeedbackStatsResponse)
def get_feedback_stats(_: None = Depends(require_api_key)) -> FeedbackStatsResponse:
    return feedback_stats()
