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
    clothing_size: ClothingSize = "unknown"
    top_size: ClothingSize = "unknown"
    bottom_size: ClothingSize = "unknown"
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
    clothing_size: ClothingSize = "unknown"
    top_size: ClothingSize = "unknown"
    bottom_size: ClothingSize = "unknown"
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
    top_k: int = Field(default=3, ge=1, le=10)


class UserProfile(BaseModel):
    user_id: str
    gender: Gender = "unknown"
    age: int = Field(ge=10, le=100)
    height_cm: int = Field(ge=120, le=230)
    clothing_size: ClothingSize = "unknown"
    top_size: ClothingSize = "unknown"
    bottom_size: ClothingSize = "unknown"
    shoe_size: str = "unknown"
    style_preferences: list[str] = Field(default_factory=list)
    body_shape: BodyShape | None = None
    body_measurements: BodyMeasurements | None = None
    location: str = ""


class OpenWeatherMain(BaseModel):
    temp: float


class OpenWeatherCondition(BaseModel):
    main: str = "clear"


class OpenWeatherResponse(BaseModel):
    main: OpenWeatherMain
    weather: list[OpenWeatherCondition] = Field(default_factory=list)


class OutfitSuggestion(BaseModel):
    outfit_id: str
    outfit_label: str
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    user_id: str
    inferred_body_shape: BodyShape
    dominant_occasion: str
    weather_bucket: str
    suggestions: list[OutfitSuggestion]


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


FeedbackEventType = Literal["impression", "click", "selected", "dismissed"]


class FeedbackEventRequest(BaseModel):
    session_id: str
    user_id: str
    outfit_id: str
    event_type: FeedbackEventType
    timestamp: datetime | None = None
    position: int | None = Field(default=None, ge=0)
    gender: Gender = "unknown"
    age: int = Field(ge=10, le=100)
    height_cm: int = Field(ge=120, le=230)
    clothing_size: ClothingSize = "unknown"
    top_size: ClothingSize = "unknown"
    bottom_size: ClothingSize = "unknown"
    shoe_size: str = "unknown"
    body_shape: BodyShape = "unknown"
    style_preferences: list[str] = Field(default_factory=list)
    dominant_occasion: str = "casual"
    weather_bucket: str = "mild"


class FeedbackEventResponse(BaseModel):
    status: str
    event_id: str


class FeedbackStatsResponse(BaseModel):
    total_events: int
    unique_users: int
    unique_sessions: int
    event_type_counts: dict[str, int]


class FeedbackBatchRequest(BaseModel):
    events: list[FeedbackEventRequest] = Field(default_factory=list, min_length=1)


class FeedbackBatchResponse(BaseModel):
    status: str
    created_count: int
    event_ids: list[str]
