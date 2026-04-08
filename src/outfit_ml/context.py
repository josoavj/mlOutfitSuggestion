from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .schemas import AgendaEntry, OpenWeatherResponse, UserProfile, WeatherInput


class OpenWeatherError(RuntimeError):
    pass


class AppIntegrationError(RuntimeError):
    pass


def _data_source() -> str:
    # Supported values: "api" (default) or "file".
    return os.getenv("MAGICMIRROR_DATA_SOURCE", "api").strip().lower()


def _load_json_file(path: Path) -> dict | list:
    if not path.exists():
        raise AppIntegrationError(f"Fichier introuvable: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:  # noqa: BLE001
        raise AppIntegrationError(f"JSON invalide: {path}") from exc


def _app_base_url() -> str:
    base = os.getenv("MAGICMIRROR_API_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise AppIntegrationError("MAGICMIRROR_API_BASE_URL manquante")
    return base


def _http_get_json(url: str) -> dict | list:
    token = os.getenv("MAGICMIRROR_API_TOKEN", "").strip()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
            payload = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise AppIntegrationError("Echec de connexion a l'API application") from exc

    if status >= 400:
        raise AppIntegrationError(f"API application a retourne un statut {status}")
    return json.loads(payload)


def fetch_openweather(location: str) -> WeatherInput:
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
        raise OpenWeatherError("Echec de connexion a OpenWeather") from exc

    if status >= 400:
        raise OpenWeatherError(f"OpenWeather a retourne un statut {status}")

    data = OpenWeatherResponse.model_validate(json.loads(payload))
    condition = data.weather[0].main if data.weather else "clear"
    return WeatherInput(temperature_c=data.main.temp, condition=condition)


def agenda_to_labels(entries: list[AgendaEntry]) -> list[str]:
    labels: list[str] = []
    for entry in entries:
        text = " ".join([entry.title, entry.category, " ".join(entry.tags)]).lower().strip()
        if not text:
            continue

        if any(key in text for key in ["meeting", "bureau", "travail", "work"]):
            labels.append("work")
        elif any(key in text for key in ["sport", "gym", "running", "yoga"]):
            labels.append("sport")
        elif any(key in text for key in ["date", "diner", "dinner"]):
            labels.append("date")
        elif any(key in text for key in ["event", "soir", "party", "mariage"]):
            labels.append("event")
        elif any(key in text for key in ["trip", "voyage", "outdoor", "randonnee"]):
            labels.append("outdoor")
        else:
            labels.append("casual")

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
    else:
        raise AppIntegrationError("MAGICMIRROR_DATA_SOURCE doit etre 'api' ou 'file'")

    if not isinstance(raw, dict):
        raise AppIntegrationError("Profil utilisateur invalide")

    measurements = raw.get("body_measurements") or {}
    location = raw.get("location") or raw.get("city") or ""
    return UserProfile(
        user_id=str(raw.get("user_id") or user_id),
        gender=str(raw.get("gender") or "unknown"),
        age=int(raw.get("age")),
        height_cm=int(raw.get("height_cm")),
        clothing_size=str(raw.get("clothing_size") or "unknown").lower(),
        top_size=str(raw.get("top_size") or "unknown").lower(),
        bottom_size=str(raw.get("bottom_size") or "unknown").lower(),
        shoe_size=str(raw.get("shoe_size") or "unknown").lower(),
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
    else:
        raise AppIntegrationError("MAGICMIRROR_DATA_SOURCE doit etre 'api' ou 'file'")

    entries_raw: list[dict]
    if isinstance(raw, list):
        entries_raw = [item for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        possible = raw.get("entries") or raw.get("events") or []
        entries_raw = [item for item in possible if isinstance(item, dict)]
    else:
        raise AppIntegrationError("Agenda invalide")

    entries: list[AgendaEntry] = []
    for item in entries_raw:
        title = item.get("title") or item.get("name") or ""
        category = item.get("category") or item.get("type") or ""
        tags = item.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        entries.append(
            AgendaEntry(
                title=str(title),
                category=str(category),
                tags=[str(tag) for tag in tags],
            )
        )

    return entries
