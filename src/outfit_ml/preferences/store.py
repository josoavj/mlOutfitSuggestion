"""Persistance des préférences utilisateur.

Même principe que wardrobe/store.py : un fichier JSON par utilisateur,
remplaçable plus tard par un vrai backend sans changer l'interface.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    MicroSurveyKind,
    MicroSurveyResponse,
    OnboardingSubmission,
    PreferencesPatch,
    UserPreferences,
)


def sanitize_user_id(user_id: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', str(user_id or '')).strip()
    if not cleaned:
        return "default_user"
    return cleaned


PREFERENCES_DATA_ROOT = Path(os.getenv("PREFERENCES_DATA_ROOT", "data/preferences"))
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "file").strip().lower()


class PreferencesStore:
    def __init__(self, data_root: Path = PREFERENCES_DATA_ROOT):
        self.data_root = data_root
        self.data_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db_store = None

    def _get_db(self):
        if self._db_store is None:
            from ..db_store import DatabaseStore
            self._db_store = DatabaseStore()
        return self._db_store

    def _user_file(self, user_id: str) -> Path:
        safe_id = sanitize_user_id(user_id)
        return self.data_root / f"{safe_id}.json"

    def get(self, user_id: str) -> UserPreferences:
        if STORAGE_BACKEND == "sqlite":
            return self._get_db().get_preferences(user_id)

        with self._lock:
            path = self._user_file(user_id)
            if not path.exists():
                return UserPreferences(user_id=user_id)
            with path.open("r", encoding="utf-8") as f:
                return UserPreferences.model_validate(json.load(f))

    def _save(self, prefs: UserPreferences) -> None:
        path = self._user_file(prefs.user_id)
        with path.open("w", encoding="utf-8") as f:
            f.write(prefs.model_dump_json(indent=2))

    def is_onboarded(self, user_id: str) -> bool:
        return self.get(user_id).onboarding_completed_at is not None

    def submit_onboarding(self, user_id: str, payload: OnboardingSubmission) -> UserPreferences:
        if STORAGE_BACKEND == "sqlite":
            return self._get_db().submit_onboarding(user_id, payload)

        prefs = UserPreferences(
            user_id=user_id,
            styles_aimes=payload.styles_aimes,
            styles_evites=payload.styles_evites,
            couleurs_aimees=payload.couleurs_aimees,
            couleurs_evitees=payload.couleurs_evitees,
            niveau_formalite_prefere=payload.niveau_formalite_prefere,
            tolerance_meteo=payload.tolerance_meteo,
            onboarding_completed_at=datetime.now(),
            preferences_version=1,
        )
        with self._lock:
            self._save(prefs)
        return prefs

    def patch(self, user_id: str, payload: PreferencesPatch) -> UserPreferences:
        if STORAGE_BACKEND == "sqlite":
            return self._get_db().patch_preferences(user_id, payload)

        with self._lock:
            prefs = self.get(user_id)
            updates = payload.model_dump(exclude_unset=True)
            for field, value in updates.items():
                setattr(prefs, field, value)
            prefs.preferences_version += 1
            self._save(prefs)
        return prefs

    def apply_micro_survey_response(self, user_id: str, response: MicroSurveyResponse) -> UserPreferences:
        if STORAGE_BACKEND == "sqlite":
            return self._get_db().apply_micro_survey_response(user_id, response)

        with self._lock:
            prefs = self.get(user_id)

            if response.accepted:
                if response.kind == MicroSurveyKind.ban_item and response.item_id:
                    if response.item_id not in prefs.items_bannis:
                        prefs.items_bannis.append(response.item_id)
                elif response.kind == MicroSurveyKind.style_check and response.freeform_answer:
                    if response.freeform_answer not in prefs.styles_evites:
                        prefs.styles_evites.append(response.freeform_answer)

            prefs.last_micro_survey_at = datetime.now()
            prefs.preferences_version += 1
            self._save(prefs)
        return prefs


preferences_store = PreferencesStore()
