from __future__ import annotations

from collections import Counter
import hashlib
import re
import unicodedata

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
KNOWN_SIZES = ["xs", "s", "m", "l", "xl", "xxl", "unknown"]
KNOWN_SHOE_BUCKETS = ["small", "medium", "large", "unknown"]

OCCASION_KEYWORDS: dict[str, list[str]] = {
    "work": [
        "work",
        "meeting",
        "bureau",
        "travail",
        "presentation",
        "reunion",
        "brief",
        "report",
        "rapport",
        "planning",
        "sprint",
        "standup",
        "stand up",
        "review",
        "demo",
        "client",
        "interview",
        "entretien",
        "workshop",
        "seminaire",
        "seminar",
        "webinar",
        "pitch",
        "negociation",
        "audit",
        "rendez vous pro",
        "rdv pro",
        "rdv",
        "pro",
        "professionnel",
        "office",
        "business",
        "ecole",
        "universite",
        "formation",
        "cours",
        "exam",
        "examen",
    ],
    "sport": [
        "sport",
        "gym",
        "running",
        "jogging",
        "yoga",
        "basket",
        "football",
        "foot",
        "tennis",
        "muscu",
        "fitness",
        "pilates",
        "velo",
        "natation",
        "swim",
        "piscine",
        "crossfit",
        "boxe",
        "danse",
        "zumba",
        "marche",
        "trail",
        "escalade",
        "badminton",
        "rugby",
        "ski",
        "surf",
        "skate",
        "snowboard",
        "padel",
        "handball",
        "volley",
        "golf",
    ],
    "date": [
        "date",
        "rencard",
        "diner",
        "dinner",
        "romantique",
        "couple",
        "restaurant",
        "cine",
        "cinema",
        "bar",
        "verre",
        "apero",
        "aperitif",
    ],
    "event": [
        "event",
        "soir",
        "party",
        "mariage",
        "concert",
        "festival",
        "anniversaire",
        "ceremonie",
        "reception",
        "gala",
        "conference",
        "cocktail",
        "afterwork",
        "soiree",
        "expo",
        "exposition",
        "vernissage",
    ],
    "outdoor": [
        "trip",
        "voyage",
        "outdoor",
        "randonnee",
        "camping",
        "hiking",
        "plage",
        "beach",
        "balade",
        "promenade",
        "roadtrip",
        "weekend",
        "week end",
        "montagne",
        "trek",
        "trekking",
        "vacances",
    ],
    "casual": [
        "peinture",
        "painting",
        "dessin",
        "atelier",
        "art",
        "lecture",
        "bibliotheque",
        "cinema",
        "shopping",
        "jeux",
        "gaming",
        "detente",
        "famille",
        "maison",
        "teletravail",
        "courses",
        "supermarche",
        "brunch",
        "cafe",
        "home",
        "netflix",
        "serie",
        "series",
        "movie",
        "chill",
        "repos",
        "cuisine",
        "cooking",
        "menage",
    ],
}

SUBLABEL_KEYWORDS: dict[str, list[tuple[str, str]]] = {
    "work": [
        ("presentation", "presentation"),
        ("brief", "brief"),
        ("client", "client"),
        ("review", "review"),
        ("planning", "planning"),
        ("reunion", "reunion"),
        ("standup", "standup"),
        ("webinar", "webinar"),
        ("workshop", "workshop"),
        ("seminaire", "seminaire"),
        ("interview", "interview"),
        ("formation", "formation"),
        ("cours", "cours"),
        ("examen", "examen"),
    ],
    "sport": [
        ("running", "running"),
        ("yoga", "yoga"),
        ("fitness", "fitness"),
        ("natation", "natation"),
        ("tennis", "tennis"),
        ("boxe", "boxe"),
        ("danse", "danse"),
        ("padel", "padel"),
        ("ski", "ski"),
        ("surf", "surf"),
    ],
    "event": [
        ("mariage", "mariage"),
        ("concert", "concert"),
        ("festival", "festival"),
        ("anniversaire", "anniversaire"),
        ("gala", "gala"),
        ("conference", "conference"),
        ("cocktail", "cocktail"),
        ("soiree", "soiree"),
        ("exposition", "exposition"),
    ],
    "outdoor": [
        ("randonnee", "randonnee"),
        ("camping", "camping"),
        ("hiking", "hiking"),
        ("plage", "plage"),
        ("roadtrip", "roadtrip"),
        ("weekend", "weekend"),
        ("trek", "trek"),
        ("vacances", "vacances"),
    ],
    "date": [
        ("diner", "diner"),
        ("restaurant", "restaurant"),
        ("cinema", "cinema"),
        ("romantique", "romantique"),
        ("bar", "bar"),
        ("apero", "apero"),
    ],
    "casual": [
        ("shopping", "shopping"),
        ("famille", "famille"),
        ("maison", "maison"),
        ("courses", "courses"),
        ("brunch", "brunch"),
        ("cafe", "cafe"),
        ("netflix", "netflix"),
        ("cuisine", "cuisine"),
    ],
}


def _normalize_text(value: str) -> str:
    lowered = value.strip().lower()
    # Remove accents to match both "natation" and "natátion" like variants.
    no_accents = "".join(
        char for char in unicodedata.normalize("NFD", lowered) if unicodedata.category(char) != "Mn"
    )
    alnum_spaces = re.sub(r"[^a-z0-9\s]", " ", no_accents)
    return re.sub(r"\s+", " ", alnum_spaces).strip()


def classify_agenda_text(value: str) -> str:
    text = _normalize_text(value)
    if not text:
        return "casual"

    primary = "casual"
    for label in ["work", "sport", "date", "event", "outdoor", "casual"]:
        for keyword in OCCASION_KEYWORDS[label]:
            if keyword in text:
                primary = label
                break
        if primary != "casual":
            break

    for keyword, sublabel in SUBLABEL_KEYWORDS.get(primary, []):
        if keyword in text:
            return f"{primary} - {sublabel}"
    return primary


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
        label = classify_agenda_text(item)
        mapped.append(label.split(" - ", 1)[0])

    return Counter(mapped).most_common(1)[0][0]


def encode_style_flags(style_preferences: list[str]) -> dict[str, int]:
    pref_set = {s.strip().lower() for s in style_preferences}
    return {f"pref_{style}": int(style in pref_set) for style in KNOWN_STYLES}


def normalize_size(value: str | None) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in KNOWN_SIZES else "unknown"


def shoe_size_bucket(value: str | None) -> str:
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return "unknown"

    try:
        parsed = float(raw)
    except ValueError:
        return "unknown"

    if parsed < 39:
        return "small"
    if parsed <= 43:
        return "medium"
    return "large"


def preferred_size_for_item(item_id: str, channel: str) -> str:
    digest = hashlib.sha256(f"{item_id}:{channel}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(KNOWN_SIZES[:-1])
    return KNOWN_SIZES[index]


def preferred_shoe_bucket_for_item(item_id: str) -> str:
    digest = hashlib.sha256(f"{item_id}:shoe".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(KNOWN_SHOE_BUCKETS[:-1])
    return KNOWN_SHOE_BUCKETS[index]
