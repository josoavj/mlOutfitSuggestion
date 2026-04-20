from __future__ import annotations

from dataclasses import dataclass


ALLOWED_GENDERS = {"female", "male", "non_binary", "unknown"}
ALLOWED_BODY_SHAPES = {
    "hourglass",
    "rectangle",
    "pear",
    "inverted_triangle",
    "oval",
    "unknown",
}
ALLOWED_CLOTHING_SIZES = {"xs", "s", "m", "l", "xl", "xxl", "unknown"}
ALLOWED_EVENT_TYPES = {"impression", "click", "selected", "dismissed"}
ALLOWED_WEATHER_BUCKETS = {"cold", "mild", "hot", "rainy"}
ALLOWED_OCCASIONS = {"work", "meeting", "casual", "sport", "event", "date", "outdoor"}


@dataclass(frozen=True)
class TableContract:
    table_name: str
    required_columns: tuple[str, ...]
    primary_key_hint: tuple[str, ...]


USERS_CONTRACT = TableContract(
    table_name="users",
    required_columns=(
        "user_id",
        "gender",
        "age",
        "height_cm",
        "body_shape",
        "clothing_size",
        "top_size",
        "bottom_size",
        "shoe_size",
        "style_preferences",
        "location_home",
        "updated_at",
    ),
    primary_key_hint=("user_id",),
)

OUTFITS_CONTRACT = TableContract(
    table_name="outfits_catalog",
    required_columns=(
        "outfit_id",
        "label",
        "styles",
        "occasions",
        "weather_compatibility",
        "fit_profiles",
        "formality_level",
        "season",
    ),
    primary_key_hint=("outfit_id",),
)

SESSIONS_CONTRACT = TableContract(
    table_name="context_sessions",
    required_columns=(
        "session_id",
        "user_id",
        "timestamp",
        "location",
        "weather_bucket",
        "temperature_c",
        "agenda_labels",
        "camera_confidence",
    ),
    primary_key_hint=("session_id",),
)

IMPRESSIONS_CONTRACT = TableContract(
    table_name="recommendation_impressions",
    required_columns=(
        "session_id",
        "user_id",
        "outfit_id",
        "rank_position",
        "score_model",
        "shown_at",
    ),
    primary_key_hint=("session_id", "outfit_id", "shown_at"),
)

INTERACTIONS_CONTRACT = TableContract(
    table_name="interactions",
    required_columns=(
        "session_id",
        "user_id",
        "outfit_id",
        "event_type",
        "event_time",
        "dwell_time_ms",
    ),
    primary_key_hint=("session_id", "outfit_id", "event_type", "event_time"),
)

ALL_CONTRACTS = (
    USERS_CONTRACT,
    OUTFITS_CONTRACT,
    SESSIONS_CONTRACT,
    IMPRESSIONS_CONTRACT,
    INTERACTIONS_CONTRACT,
)
