"""Tests de sécurité et de performance pour Outfit Suggestion."""

import pytest
from pathlib import Path
from fastapi import HTTPException

from ..api import require_api_key
from ..db_store import DatabaseStore
from ..wardrobe.store import WardrobeStore, sanitize_user_id


def test_sanitize_user_id():
    assert sanitize_user_id("user_123") == "user_123"
    assert sanitize_user_id("../../etc/passwd") == "etcpasswd"
    assert sanitize_user_id("  user..name!!  ") == "username"
    assert sanitize_user_id("///") == "default_user"


def test_base64_upload_size_limit(tmp_path: Path):
    store = WardrobeStore(data_root=tmp_path / "wardrobe", image_root=tmp_path / "images")

    # Image fictive Base64 de 7 Mo (dépasse 5 Mo)
    large_payload = "data:image/png;base64," + ("A" * (7 * 1024 * 1024))
    with pytest.raises(ValueError, match="dépasse"):
        store._persist_image("user_test", large_payload)


def test_api_key_constant_time_verification(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEY", "secret_key_123")

    # Clé valide : passe sans exception
    require_api_key(x_api_key="secret_key_123")

    # Clé invalide : lève HTTPException(401)
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(x_api_key="wrong_key")
    assert exc_info.value.status_code == 401


def test_sqlite_wal_mode(tmp_path: Path):
    db_file = tmp_path / "test_wal.db"
    db = DatabaseStore(db_path=db_file)

    conn = db._get_connection()
    cursor = conn.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal"
