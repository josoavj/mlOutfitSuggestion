"""Backend de stockage SQLite pour WardrobeStore et PreferencesStore.

Permet le stockage relationnel/multi-utilisateurs haute performance tout en
conservant la rétrocompatibilité parfaite avec les adaptateurs JSON existants.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .preferences.models import (
    MicroSurveyKind,
    MicroSurveyResponse,
    OnboardingSubmission,
    PreferencesPatch,
    UserPreferences,
)
from .wardrobe.models import (
    WardrobeItem,
    WardrobeItemCreate,
    WardrobeItemUpdate,
)
from .wardrobe.store import WardrobeItemNotFound

DEFAULT_DB_PATH = Path("data/app_database.db")


class DatabaseStore:
    """Store unifié SQLite gérant à la fois la garde-robe et les préférences."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wardrobe_items (
                    item_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wardrobe_user_cat
                ON wardrobe_items (user_id, category);
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    preferences_version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.commit()

    # ---------------------------------------------------------------------------
    # Methodes Wardrobe
    # ---------------------------------------------------------------------------

    def create_wardrobe_item(self, user_id: str, payload: WardrobeItemCreate, image_url: Optional[str] = None) -> WardrobeItem:
        item = WardrobeItem.from_create(user_id, payload, image_url)
        raw_json = item.model_dump_json()
        now = datetime.now().isoformat()

        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO wardrobe_items (item_id, user_id, category, subcategory, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item.item_id, user_id, item.category, item.subcategory, raw_json, now, now),
            )
            conn.commit()
        return item

    def list_wardrobe_items(self, user_id: str, category: Optional[str] = None) -> list[WardrobeItem]:
        query = "SELECT data_json FROM wardrobe_items WHERE user_id = ?"
        params: list[str] = [user_id]
        if category:
            query += " AND category = ?"
            params.append(category)

        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [WardrobeItem.model_validate_json(row["data_json"]) for row in rows]

    def get_wardrobe_item(self, user_id: str, item_id: str) -> WardrobeItem:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT data_json FROM wardrobe_items WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )
            row = cursor.fetchone()

        if not row:
            raise WardrobeItemNotFound(item_id)
        return WardrobeItem.model_validate_json(row["data_json"])

    def update_wardrobe_item(self, user_id: str, item_id: str, payload: WardrobeItemUpdate) -> WardrobeItem:
        item = self.get_wardrobe_item(user_id, item_id)
        updates = payload.model_dump(exclude_unset=True)

        item_dict = json.loads(item.model_dump_json())
        item_dict.update(updates)
        item_dict["updated_at"] = datetime.now().isoformat()
        updated_item = WardrobeItem.model_validate(item_dict)

        now = datetime.now().isoformat()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                UPDATE wardrobe_items
                SET category = ?, subcategory = ?, data_json = ?, updated_at = ?
                WHERE user_id = ? AND item_id = ?
                """,
                (updated_item.category, updated_item.subcategory, updated_item.model_dump_json(), now, user_id, item_id),
            )
            conn.commit()

        return updated_item

    def delete_wardrobe_item(self, user_id: str, item_id: str) -> None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM wardrobe_items WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise WardrobeItemNotFound(item_id)

    def mark_wardrobe_suggested(self, user_id: str, item_ids: list[str]) -> None:
        if not item_ids:
            return
        now = datetime.now().isoformat()
        items = self.list_wardrobe_items(user_id)
        with self._lock, self._get_connection() as conn:
            for item in items:
                if item.item_id in item_ids:
                    item_dict = json.loads(item.model_dump_json())
                    item_dict["last_suggested_at"] = now
                    updated = WardrobeItem.model_validate(item_dict)
                    conn.execute(
                        "UPDATE wardrobe_items SET data_json = ?, updated_at = ? WHERE user_id = ? AND item_id = ?",
                        (updated.model_dump_json(), now, user_id, item.item_id),
                    )
            conn.commit()

    # ---------------------------------------------------------------------------
    # Methodes Preferences
    # ---------------------------------------------------------------------------

    def get_preferences(self, user_id: str) -> UserPreferences:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT data_json FROM user_preferences WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

        if not row:
            return UserPreferences(user_id=user_id)
        return UserPreferences.model_validate_json(row["data_json"])

    def save_preferences(self, prefs: UserPreferences) -> None:
        now = datetime.now().isoformat()
        raw_json = prefs.model_dump_json()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, data_json, preferences_version, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    preferences_version = excluded.preferences_version,
                    updated_at = excluded.updated_at
                """,
                (prefs.user_id, raw_json, prefs.preferences_version, now),
            )
            conn.commit()

    def submit_onboarding(self, user_id: str, payload: OnboardingSubmission) -> UserPreferences:
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
        self.save_preferences(prefs)
        return prefs

    def patch_preferences(self, user_id: str, payload: PreferencesPatch) -> UserPreferences:
        prefs = self.get_preferences(user_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(prefs, field, value)
        prefs.preferences_version += 1
        self.save_preferences(prefs)
        return prefs

    def apply_micro_survey_response(self, user_id: str, response: MicroSurveyResponse) -> UserPreferences:
        prefs = self.get_preferences(user_id)

        if response.accepted:
            if response.kind == MicroSurveyKind.ban_item and response.item_id:
                if response.item_id not in prefs.items_bannis:
                    prefs.items_bannis.append(response.item_id)
            elif response.kind == MicroSurveyKind.style_check and response.freeform_answer:
                if response.freeform_answer not in prefs.styles_evites:
                    prefs.styles_evites.append(response.freeform_answer)

        prefs.last_micro_survey_at = datetime.now()
        prefs.preferences_version += 1
        self.save_preferences(prefs)
        return prefs
