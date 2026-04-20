from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .features import classify_agenda_text
from .schemas import AgendaEntry, OpenWeatherResponse, UserProfile, WeatherInput


class OpenWeatherError(RuntimeError):
    pass


class AppIntegrationError(RuntimeError):
    pass


def _normalize_body_shape(value: object) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "hourglass": "hourglass",
        "sablier": "hourglass",
        "rectangle": "rectangle",
        "rectangulaire": "rectangle",
        "pear": "pear",
        "poire": "pear",
        "inverted_triangle": "inverted_triangle",
        "triangle inverse": "inverted_triangle",
        "oval": "oval",
        "ovale": "oval",
    }
    return mapping.get(text, "unknown")


def _data_source() -> str:
    # Supported values: "api", "file" (default) or "supabase".
    return os.getenv("MAGICMIRROR_DATA_SOURCE", "file").strip().lower()


def _load_json_file(path: Path) -> dict | list:
    if not path.exists():
        raise AppIntegrationError(f"Fichier introuvable : {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:  # noqa: BLE001
        raise AppIntegrationError(f"JSON invalide : {path}") from exc


def _app_base_url() -> str:
    base = os.getenv("MAGICMIRROR_API_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise AppIntegrationError("MAGICMIRROR_API_BASE_URL manquante")
    return base


def _http_get_json(url: str, headers_override: dict[str, str] | None = None) -> dict | list:
    token = os.getenv("MAGICMIRROR_API_TOKEN", "").strip()
    headers = {"Accept": "application/json"}
    if headers_override:
        headers.update(headers_override)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers_override:
        headers.update(headers_override)

    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            payload = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise AppIntegrationError("Échec de connexion à l'API application") from exc

    if status >= 400:
        raise AppIntegrationError(f"L'API application a retourné un statut {status}")
    return json.loads(payload)


def _supabase_rest_base() -> str:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url:
        raise AppIntegrationError("SUPABASE_URL manquante")
    return f"{url}/rest/v1"


def _supabase_headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv(
        "SUPABASE_ANON_KEY", ""
    ).strip()
    if not key:
        raise AppIntegrationError("SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY manquante")

    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def _fetch_supabase_profile(user_id: str) -> dict:
    base = _supabase_rest_base()
    headers = _supabase_headers()

    table = os.getenv("SUPABASE_PROFILE_TABLE", "profiles").strip()
    id_column = os.getenv("SUPABASE_PROFILE_USER_ID_COLUMN", "user_id").strip()

    query = urlencode({"select": "*", id_column: f"eq.{user_id}", "limit": 1})
    url = f"{base}/{table}?{query}"
    raw = _http_get_json(url, headers_override=headers)

    if not isinstance(raw, list) or not raw:
        raise AppIntegrationError(f"Profil introuvable dans Supabase pour user_id={user_id}")
    row = raw[0]
    if not isinstance(row, dict):
        raise AppIntegrationError("Profil Supabase invalide")
    return row


def _fetch_supabase_agenda(user_id: str) -> list[dict]:
    base = _supabase_rest_base()
    headers = _supabase_headers()

    table = os.getenv("SUPABASE_AGENDA_TABLE", "agenda_events").strip()
    user_column = os.getenv("SUPABASE_AGENDA_USER_ID_COLUMN", "user_id").strip()
    date_column = os.getenv("SUPABASE_AGENDA_DATE_COLUMN", "start_time").strip()
    today_only = os.getenv("SUPABASE_AGENDA_TODAY_ONLY", "true").strip().lower() == "true"

    if today_only:
        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        # PostgREST supports comparison operators directly in query string.
        url = (
            f"{base}/{table}?select=*&{user_column}=eq.{user_id}"
            f"&{date_column}=gte.{start.isoformat()}"
            f"&{date_column}=lt.{end.isoformat()}"
            f"&order={date_column}.asc"
        )
    else:
        query = urlencode(
            {
                "select": "*",
                user_column: f"eq.{user_id}",
                "order": f"{date_column}.asc",
            }
        )
        url = f"{base}/{table}?{query}"

    raw = _http_get_json(url, headers_override=headers)
    if not isinstance(raw, list):
        raise AppIntegrationError("Agenda Supabase invalide")

    rows: list[dict] = [item for item in raw if isinstance(item, dict)]
    return rows


def fetch_openweather_detailed(location: str) -> tuple[WeatherInput, OpenWeatherResponse]:
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        raise OpenWeatherError("OPENWEATHER_API_KEY manquante")

    query = urlencode({"q": location, "appid": api_key, "units": "metric"})
    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"

    try:
        with urlopen(url, timeout=10) as response:
            status = response.status
            payload = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise OpenWeatherError("Échec de connexion à OpenWeather") from exc

    if status >= 400:
        raise OpenWeatherError(f"OpenWeather a retourné un statut {status}")

    data = OpenWeatherResponse.model_validate(json.loads(payload))
    condition = data.weather[0].main if data.weather else "clear"
    weather = WeatherInput(temperature_c=data.main.temp, condition=condition)
    return weather, data


def fetch_openweather(location: str) -> WeatherInput:
    weather, _ = fetch_openweather_detailed(location)
    return weather


def agenda_to_labels(entries: list[AgendaEntry]) -> list[str]:
    labels: list[str] = []
    for entry in entries:
        text = " ".join([entry.title, entry.category, " ".join(entry.tags)]).lower().strip()
        if not text:
            continue
        labels.append(classify_agenda_text(text))

    return labels


def fetch_user_profile(user_id: str) -> UserProfile:
    source = _data_source()
    if source == "file":
        file_template = os.getenv(
            "MAGICMIRROR_PROFILE_FILE_TEMPLATE",
            "data/users/{user_id}/profile.json",
        )
        profile_path = Path(file_template.format(user_id=user_id))
        raw = _load_json_file(profile_path)
    elif source == "api":
        base = _app_base_url()
        template = os.getenv(
            "MAGICMIRROR_PROFILE_PATH_TEMPLATE",
            "/api/users/{user_id}/profile",
        )
        path = template.format(user_id=user_id)
        raw = _http_get_json(f"{base}{path}")
    elif source == "supabase":
        raw = _fetch_supabase_profile(user_id)
    else:
        raise AppIntegrationError("MAGICMIRROR_DATA_SOURCE doit être 'api', 'file' ou 'supabase'")

    if not isinstance(raw, dict):
        raise AppIntegrationError("Profil utilisateur invalide")

    gender_col = os.getenv("SUPABASE_PROFILE_GENDER_COLUMN", "gender").strip()
    age_col = os.getenv("SUPABASE_PROFILE_AGE_COLUMN", "age").strip()
    height_col = os.getenv("SUPABASE_PROFILE_HEIGHT_COLUMN", "height_cm").strip()
    body_shape_col = os.getenv("SUPABASE_PROFILE_BODY_SHAPE_COLUMN", "body_shape").strip()
    style_pref_col = os.getenv(
        "SUPABASE_PROFILE_STYLE_PREFERENCES_COLUMN", "style_preferences"
    ).strip()
    location_col = os.getenv("SUPABASE_PROFILE_LOCATION_COLUMN", "location").strip()
    clothing_size_col = os.getenv("SUPABASE_PROFILE_CLOTHING_SIZE_COLUMN", "clothing_size").strip()
    top_size_col = os.getenv("SUPABASE_PROFILE_TOP_SIZE_COLUMN", "top_size").strip()
    bottom_size_col = os.getenv("SUPABASE_PROFILE_BOTTOM_SIZE_COLUMN", "bottom_size").strip()
    shoe_size_col = os.getenv("SUPABASE_PROFILE_SHOE_SIZE_COLUMN", "shoe_size").strip()
    measurements_col = os.getenv(
        "SUPABASE_PROFILE_BODY_MEASUREMENTS_COLUMN", "body_measurements"
    ).strip()

    measurements = raw.get(measurements_col) or raw.get("body_measurements") or {}
    location = raw.get(location_col) or raw.get("location") or raw.get("city") or ""

    style_pref_raw = raw.get(style_pref_col) or raw.get("style_preferences") or []
    if isinstance(style_pref_raw, str):
        style_preferences = [v.strip() for v in style_pref_raw.split("|") if v.strip()]
    elif isinstance(style_pref_raw, list):
        style_preferences = [str(v).strip() for v in style_pref_raw if str(v).strip()]
    else:
        style_preferences = []

    return UserProfile(
        user_id=str(raw.get("user_id") or user_id),
        gender=str(raw.get("gender") or "unknown"),
        age=int(raw.get("age")),
        height_cm=int(raw.get("height_cm")),
        clothing_size=str(raw.get("clothing_size") or "unknown"),
        top_size=str(raw.get("top_size") or "unknown"),
        bottom_size=str(raw.get("bottom_size") or "unknown"),
        shoe_size=str(raw.get("shoe_size") or "unknown"),
        style_preferences=list(raw.get("style_preferences") or []),
        body_shape=raw.get("body_shape"),
        body_measurements=measurements or None,
        location=str(location),
    )


def fetch_today_agenda_entries(user_id: str) -> list[AgendaEntry]:
    source = _data_source()
    if source == "file":
        file_template = os.getenv(
            "MAGICMIRROR_AGENDA_FILE_TEMPLATE",
            "data/users/{user_id}/agenda_today.json",
        )
        agenda_path = Path(file_template.format(user_id=user_id))
        raw = _load_json_file(agenda_path)
    elif source == "api":
        base = _app_base_url()
        template = os.getenv(
            "MAGICMIRROR_AGENDA_PATH_TEMPLATE",
            "/api/users/{user_id}/agenda/today",
        )
        path = template.format(user_id=user_id)
        raw = _http_get_json(f"{base}{path}")
    elif source == "supabase":
        raw = _fetch_supabase_agenda(user_id)
    else:
        raise AppIntegrationError("MAGICMIRROR_DATA_SOURCE doit être 'api', 'file' ou 'supabase'")

    entries_raw: list[dict]
    if isinstance(raw, list):
        entries_raw = [item for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        possible = raw.get("entries") or raw.get("events") or []
        entries_raw = [item for item in possible if isinstance(item, dict)]
    else:
        raise AppIntegrationError("Agenda invalide")

    entries: list[AgendaEntry] = []
    title_col = os.getenv("SUPABASE_AGENDA_TITLE_COLUMN", "title").strip()
    category_col = os.getenv("SUPABASE_AGENDA_CATEGORY_COLUMN", "event_type").strip()
    tags_col = os.getenv("SUPABASE_AGENDA_TAGS_COLUMN", "tags").strip()

    for item in entries_raw:
        title = item.get(title_col) or item.get("name") or item.get("title") or ""
        category = (
            item.get(category_col)
            or item.get("event_type")
            or item.get("type")
            or item.get("category")
            or ""
        )
        tags = item.get(tags_col) or item.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if not tags:
            description = item.get("description")
            if isinstance(description, str) and description.strip():
                tags = [description.strip()]

        entries.append(
            AgendaEntry(
                title=str(title),
                category=str(category),
                tags=[str(tag) for tag in tags],
            )
        )

    return entries
