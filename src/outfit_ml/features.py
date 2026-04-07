from __future__ import annotations

from collections import Counter

from .schemas import BodyMeasurements


KNOWN_STYLES = [
    "classic",
    "minimalist",
    "casual",
    "sport",
    "elegant",
    "practical",
]
KNOWN_OCCASIONS = ["work", "meeting", "casual", "sport", "event", "date", "outdoor"]
KNOWN_WEATHER = ["cold", "mild", "hot", "rainy"]


def infer_body_shape(measurements: BodyMeasurements | None) -> str:
    if measurements is None:
        return "unknown"

    shoulders = measurements.shoulders_cm
    waist = measurements.waist_cm
    hips = measurements.hips_cm

    if waist == 0 or hips == 0:
        return "unknown"

    shoulder_hips_ratio = shoulders / hips
    waist_hips_ratio = waist / hips

    if 0.9 <= shoulder_hips_ratio <= 1.1 and waist_hips_ratio <= 0.75:
        return "hourglass"
    if shoulder_hips_ratio < 0.9 and waist_hips_ratio > 0.75:
        return "pear"
    if shoulder_hips_ratio > 1.1 and waist_hips_ratio > 0.75:
        return "inverted_triangle"
    if waist_hips_ratio >= 0.85:
        return "oval"
    return "rectangle"


def weather_bucket(temperature_c: float, condition: str) -> str:
    normalized = condition.strip().lower()
    if normalized in {"rain", "rainy", "storm", "drizzle"}:
        return "rainy"
    if temperature_c < 10:
        return "cold"
    if temperature_c > 24:
        return "hot"
    return "mild"


def dominant_occasion(agenda: list[str]) -> str:
    if not agenda:
        return "casual"

    mapped = []
    for item in agenda:
        value = item.strip().lower()
        if "work" in value or "meeting" in value:
            mapped.append("work")
        elif "sport" in value or "gym" in value:
            mapped.append("sport")
        elif "date" in value:
            mapped.append("date")
        elif "event" in value or "party" in value:
            mapped.append("event")
        elif "outdoor" in value or "trip" in value:
            mapped.append("outdoor")
        else:
            mapped.append("casual")

    return Counter(mapped).most_common(1)[0][0]


def encode_style_flags(style_preferences: list[str]) -> dict[str, int]:
    pref_set = {s.strip().lower() for s in style_preferences}
    return {f"pref_{style}": int(style in pref_set) for style in KNOWN_STYLES}
