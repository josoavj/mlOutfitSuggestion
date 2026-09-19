"""Persistance des items de garde-robe.

Suit le même principe que le mode fichier local déjà utilisé pour les
profils/agendas (MAGICMIRROR_DATA_SOURCE=file) : un fichier JSON par
utilisateur sous data/wardrobe/{user_id}.json. Peut être remplacé plus
tard par un vrai backend (DB) sans changer l'interface de WardrobeStore.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import WardrobeItem, WardrobeItemCreate, WardrobeItemUpdate

WARDROBE_DATA_ROOT = Path(os.getenv("WARDROBE_DATA_ROOT", "data/wardrobe"))
WARDROBE_IMAGE_ROOT = Path(os.getenv("WARDROBE_IMAGE_ROOT", "data/wardrobe/images"))


class WardrobeItemNotFound(Exception):
    pass


class WardrobeStore:
    def __init__(self, data_root: Path = WARDROBE_DATA_ROOT, image_root: Path = WARDROBE_IMAGE_ROOT):
        self.data_root = data_root
        self.image_root = image_root
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.image_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _user_file(self, user_id: str) -> Path:
        return self.data_root / f"{user_id}.json"

    def _load(self, user_id: str) -> list[dict]:
        path = self._user_file(user_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, user_id: str, items: list[dict]) -> None:
        path = self._user_file(user_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2, default=str)

    def _persist_image(self, user_id: str, image_base64: str) -> str:
        """Décode et sauvegarde une image uploadée, renvoie son URL/chemin relatif."""
        user_dir = self.image_root / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        header, _, encoded = image_base64.partition(",")
        encoded = encoded or header  # tolère un payload sans préfixe data:...
        ext = "jpg"
        if "image/png" in header:
            ext = "png"
        elif "image/webp" in header:
            ext = "webp"

        filename = f"{uuid.uuid4().hex}.{ext}"
        target = user_dir / filename
        target.write_bytes(base64.b64decode(encoded))
        return str(target)

    def create_item(self, user_id: str, payload: WardrobeItemCreate) -> WardrobeItem:
        image_url = payload.image_url
        if payload.image_base64:
            image_url = self._persist_image(user_id, payload.image_base64)

        item = WardrobeItem.from_create(user_id, payload, image_url)
        with self._lock:
            items = self._load(user_id)
            items.append(json.loads(item.model_dump_json()))
            self._save(user_id, items)
        return item

    def list_items(self, user_id: str, category: Optional[str] = None) -> list[WardrobeItem]:
        with self._lock:
            raw_items = self._load(user_id)
        items = [WardrobeItem.model_validate(raw) for raw in raw_items]
        if category:
            items = [i for i in items if i.category == category]
        return items

    def get_item(self, user_id: str, item_id: str) -> WardrobeItem:
        with self._lock:
            items = self._load(user_id)
        for raw in items:
            if raw.get("item_id") == item_id:
                return WardrobeItem.model_validate(raw)
        raise WardrobeItemNotFound(item_id)

    def update_item(self, user_id: str, item_id: str, payload: WardrobeItemUpdate) -> WardrobeItem:
        with self._lock:
            items = self._load(user_id)
            for raw in items:
                if raw.get("item_id") == item_id:
                    updates = payload.model_dump(exclude_unset=True)
                    raw.update(updates)
                    self._save(user_id, items)
                    return WardrobeItem.model_validate(raw)
        raise WardrobeItemNotFound(item_id)

    def delete_item(self, user_id: str, item_id: str) -> None:
        with self._lock:
            items = self._load(user_id)
            filtered = [raw for raw in items if raw.get("item_id") != item_id]
            if len(filtered) == len(items):
                raise WardrobeItemNotFound(item_id)
            self._save(user_id, filtered)

    def mark_suggested(self, user_id: str, item_ids: list[str]) -> None:
        """Met à jour last_suggested_at pour tous les items d'une tenue proposée
        (utilisé par le moteur de diversité, voir composition/diversity.py)."""
        with self._lock:
            items = self._load(user_id)
            now = datetime.now().isoformat()
            for raw in items:
                if raw.get("item_id") in item_ids:
                    raw["last_suggested_at"] = now
            self._save(user_id, items)


wardrobe_store = WardrobeStore()
