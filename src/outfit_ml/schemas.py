from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Gender = Literal["female", "male", "non_binary", "unknown"]
ClothingSize = Literal["xs", "s", "m", "l", "xl", "xxl", "unknown"]
BodyShape = Literal[
    "hourglass",
    "rectangle",
    "pear",
    "inverted_triangle",
    "oval",
    "unknown",
]


class BodyMeasurements(BaseModel):
    shoulders_cm: float = Field(gt=0)
    waist_cm: float = Field(gt=0)
    hips_cm: float = Field(gt=0)


class WeatherInput(BaseModel):
    temperature_c: float
    condition: str = Field(default="clear")


class AgendaEntry(BaseModel):
    title: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_id: str
    gender: Gender = "unknown"
    age: int = Field(ge=10, le=100)
    height_cm: int = Field(ge=120, le=230)
    clothing_size: str = "unknown"
    top_size: str = "unknown"
    bottom_size: str = "unknown"
    shoe_size: str = "unknown"
    style_preferences: list[str] = Field(default_factory=list)
    body_shape: BodyShape | None = None
    body_measurements: BodyMeasurements | None = None
    agenda: list[str] = Field(default_factory=list)
    location: str = ""
    weather: WeatherInput
    top_k: int = Field(default=3, ge=1, le=10)


class ContextRecommendationRequest(BaseModel):
    user_id: str
    gender: Gender = "unknown"
    age: int = Field(ge=10, le=100)
    height_cm: int = Field(ge=120, le=230)
    clothing_size: str = "unknown"
    top_size: str = "unknown"
    bottom_size: str = "unknown"
    shoe_size: str = "unknown"
    style_preferences: list[str] = Field(default_factory=list)
    body_shape: BodyShape | None = None
    body_measurements: BodyMeasurements | None = None
    agenda_entries: list[AgendaEntry] = Field(default_factory=list)
    location: str
    top_k: int = Field(default=3, ge=1, le=10)


class AutoRecommendationRequest(BaseModel):
    user_id: str
    location: str | None = None
    gender: Gender | None = None
    age: int | None = Field(default=None, ge=10, le=100)
    height_cm: int | None = Field(default=None, ge=120, le=230)
    clothing_size: str | None = None
    top_size: str | None = None
    bottom_size: str | None = None
    shoe_size: str | None = None
    style_preferences: list[str] | None = None
    body_shape: BodyShape | None = None
    body_measurements: BodyMeasurements | None = None
    agenda: list[str] | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class UserProfile(BaseModel):
    user_id: str
    gender: Gender = "unknown"
    age: int = Field(ge=10, le=100)
    height_cm: int = Field(ge=120, le=230)
    clothing_size: str = "unknown"
    top_size: str = "unknown"
    bottom_size: str = "unknown"
    shoe_size: str = "unknown"
    style_preferences: list[str] = Field(default_factory=list)
    body_shape: BodyShape | None = None
    body_measurements: BodyMeasurements | None = None
    location: str = ""


class OpenWeatherMain(BaseModel):
    temp: float
    feels_like: float | None = None
    humidity: int | None = None


class OpenWeatherCondition(BaseModel):
    main: str = "clear"
    description: str | None = None


class OpenWeatherWind(BaseModel):
    speed: float | None = None


class OpenWeatherSys(BaseModel):
    country: str | None = None


class OpenWeatherResponse(BaseModel):
    name: str | None = None
    sys: OpenWeatherSys | None = None
    main: OpenWeatherMain
    weather: list[OpenWeatherCondition] = Field(default_factory=list)
    wind: OpenWeatherWind | None = None


class OpenWeatherResolved(BaseModel):
    city: str = ""
    country: str = ""
    temperature_c: float
    feels_like_c: float | None = None
    humidity_percent: int | None = None
    condition: str = "clear"
    description: str = ""
    wind_speed_m_s: float | None = None


class RecommendationResolvedContext(BaseModel):
    source: Literal["manual", "context", "auto"]
    location: str = ""
    weather: WeatherInput
    openweather: OpenWeatherResolved | None = None
    agenda_labels: list[str] = Field(default_factory=list)


class OutfitSuggestion(BaseModel):
    outfit_id: str
    outfit_label: str
    outfit_items: list[str] = Field(default_factory=list)
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    user_id: str
    inferred_body_shape: BodyShape
    dominant_occasion: str
    weather_bucket: str
    suggestions: list[OutfitSuggestion]
    resolved_context: RecommendationResolvedContext | None = None


class FaceEnrollRequest(BaseModel):
    user_id: str
    image_base64: str


class FaceEnrollResponse(BaseModel):
    user_id: str
    status: str


class FaceIdentifyRequest(BaseModel):
    image_base64: str
    threshold: float = Field(default=0.45, gt=0.0, le=1.0)
    max_results: int = Field(default=1, ge=1, le=5)


class FaceMatch(BaseModel):
    user_id: str
    distance: float
    confidence: float


class FaceIdentifyResponse(BaseModel):
    matches: list[FaceMatch]


class CameraRecommendationRequest(BaseModel):
    image_base64: str
    location: str | None = None
    threshold: float = Field(default=0.45, gt=0.0, le=1.0)
    top_k: int = Field(default=3, ge=1, le=10)


class CameraRecommendationResponse(BaseModel):
    matched_user_id: str
    face_match: FaceMatch
    recommendation: RecommendationResponse


class FeedbackEventRequest(BaseModel):
    user_id: str
    event_type: str
    outfit_id: str | None = None
    score: float | None = None
    session_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class FeedbackEventResponse(BaseModel):
    status: Literal["ok"] = "ok"


class FeedbackBatchRequest(BaseModel):
    events: list[FeedbackEventRequest] = Field(default_factory=list)


class FeedbackBatchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    accepted: int = 0


class FeedbackStatsResponse(BaseModel):
    total_events: int = 0
    unique_users: int = 0
    unique_sessions: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
