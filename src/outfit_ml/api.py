from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from dotenv import load_dotenv
from fastapi.responses import FileResponse

from .context import (
    AppIntegrationError,
    OpenWeatherError,
    agenda_to_labels,
    fetch_openweather_detailed,
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
    OpenWeatherResponse,
    OpenWeatherResolved,
    RecommendationRequest,
    RecommendationResolvedContext,
    RecommendationResponse,
)
from .vision import FaceRegistry, VisionError, VisionUnavailableError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"
MODEL_METRICS_PATH = PROJECT_ROOT / "models" / "outfit_ranker_metrics.json"
FEEDBACK_EVENTS_PATH = PROJECT_ROOT / "data" / "feedback" / "events.jsonl"


load_dotenv()


def _append_feedback_event(event: FeedbackEventRequest) -> None:
    FEEDBACK_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "user_id": event.user_id,
        "event_type": event.event_type,
        "outfit_id": event.outfit_id,
        "score": event.score,
        "session_id": event.session_id,
        "metadata": event.metadata,
    }
    with FEEDBACK_EVENTS_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _iter_feedback_events() -> list[dict]:
    if not FEEDBACK_EVENTS_PATH.exists():
        return []

    events: list[dict] = []
    with FEEDBACK_EVENTS_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                events.append(item)
    return events


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
        raise HTTPException(status_code=401, detail="Clé API invalide")


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


@app.post("/feedback/event", response_model=FeedbackEventResponse)
def feedback_event(request: FeedbackEventRequest, _: None = Depends(require_api_key)) -> FeedbackEventResponse:
    _append_feedback_event(request)
    return FeedbackEventResponse()


@app.post("/feedback/batch", response_model=FeedbackBatchResponse)
def feedback_batch(request: FeedbackBatchRequest, _: None = Depends(require_api_key)) -> FeedbackBatchResponse:
    accepted = 0
    for event in request.events:
        _append_feedback_event(event)
        accepted += 1
    return FeedbackBatchResponse(accepted=accepted)


@app.get("/feedback/stats", response_model=FeedbackStatsResponse)
def feedback_stats(_: None = Depends(require_api_key)) -> FeedbackStatsResponse:
    events = _iter_feedback_events()
    type_counts = Counter(str(item.get("event_type") or "unknown") for item in events)
    unique_users = {
        str(item.get("user_id"))
        for item in events
        if item.get("user_id")
    }
    unique_sessions = {
        str(item.get("session_id"))
        for item in events
        if item.get("session_id")
    }

    return FeedbackStatsResponse(
        total_events=len(events),
        unique_users=len(unique_users),
        unique_sessions=len(unique_sessions),
        event_type_counts=dict(type_counts),
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


def _resolve_openweather_payload(openweather: OpenWeatherResponse) -> OpenWeatherResolved:
    primary = openweather.weather[0] if openweather.weather else None
    return OpenWeatherResolved(
        city=openweather.name or "",
        country=(openweather.sys.country if openweather.sys and openweather.sys.country else ""),
        temperature_c=openweather.main.temp,
        feels_like_c=openweather.main.feels_like,
        humidity_percent=openweather.main.humidity,
        condition=(primary.main if primary and primary.main else "clear"),
        description=(primary.description if primary and primary.description else ""),
        wind_speed_m_s=(openweather.wind.speed if openweather.wind else None),
    )


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
            "data_source": os.getenv("MAGICMIRROR_DATA_SOURCE", "file").strip().lower(),
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
        response = recommender.recommend(request)
        response.resolved_context = RecommendationResolvedContext(
            source="manual",
            location=request.location,
            weather=request.weather,
            agenda_labels=request.agenda,
        )
        return response
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Modèle absent. Lance d'abord l'entraînement.",
        ) from exc


@app.post("/recommend/context", response_model=RecommendationResponse)
def recommend_from_context(
    request: ContextRecommendationRequest,
    _: None = Depends(require_api_key),
) -> RecommendationResponse:
    try:
        weather, openweather = fetch_openweather_detailed(request.location)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    agenda_labels = agenda_to_labels(request.agenda_entries)

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
        agenda=agenda_labels,
        location=request.location,
        weather=weather,
        top_k=request.top_k,
    )
    response = recommend(base_request)
    response.resolved_context = RecommendationResolvedContext(
        source="context",
        location=request.location,
        weather=weather,
        openweather=_resolve_openweather_payload(openweather),
        agenda_labels=agenda_labels,
    )
    return response


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
            detail="Localisation absente : fournir request.location ou location dans le profil.",
        )

    try:
        weather, openweather = fetch_openweather_detailed(resolved_location)
    except OpenWeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    agenda_labels = request.agenda if request.agenda else agenda_to_labels(agenda_entries)
    resolved_gender = request.gender or profile.gender
    resolved_age = request.age if request.age is not None else profile.age
    resolved_height_cm = request.height_cm if request.height_cm is not None else profile.height_cm
    resolved_clothing_size = request.clothing_size if request.clothing_size is not None else profile.clothing_size
    resolved_top_size = request.top_size if request.top_size is not None else profile.top_size
    resolved_bottom_size = request.bottom_size if request.bottom_size is not None else profile.bottom_size
    resolved_shoe_size = request.shoe_size if request.shoe_size is not None else profile.shoe_size
    resolved_style_preferences = (
        request.style_preferences
        if request.style_preferences is not None
        else profile.style_preferences
    )
    resolved_body_shape = request.body_shape if request.body_shape is not None else profile.body_shape
    resolved_body_measurements = (
        request.body_measurements
        if request.body_measurements is not None
        else profile.body_measurements
    )

    base_request = RecommendationRequest(
        user_id=profile.user_id,
        gender=resolved_gender,
        age=resolved_age,
        height_cm=resolved_height_cm,
        clothing_size=resolved_clothing_size,
        top_size=resolved_top_size,
        bottom_size=resolved_bottom_size,
        shoe_size=resolved_shoe_size,
        style_preferences=resolved_style_preferences,
        body_shape=resolved_body_shape,
        body_measurements=resolved_body_measurements,
        agenda=agenda_labels,
        location=resolved_location,
        weather=weather,
        top_k=request.top_k,
    )
    response = recommend(base_request)
    response.resolved_context = RecommendationResolvedContext(
        source="auto",
        location=resolved_location,
        weather=weather,
        openweather=_resolve_openweather_payload(openweather),
        agenda_labels=agenda_labels,
    )
    return response


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
            detail="Aucun utilisateur reconnu. Faire l'enrôlement via /vision/enroll.",
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
