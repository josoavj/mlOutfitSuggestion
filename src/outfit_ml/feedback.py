from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .schemas import FeedbackEventRequest, FeedbackStatsResponse


_FEEDBACK_BUFFER: list[dict] = []
_FEEDBACK_LOCK = threading.Lock()
_LAST_FLUSH_TS = 0.0


def _feedback_flush_interval_seconds() -> int:
    raw = os.getenv("FEEDBACK_FLUSH_EVERY", "5").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 5


def _feedback_buffer_size() -> int:
    raw = os.getenv("FEEDBACK_BUFFER_SIZE", "10").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 10


def _feedback_log_path() -> Path:
    raw_path = os.getenv("FEEDBACK_LOG_PATH", "data/feedback/events.jsonl").strip()
    return Path(raw_path)


def _flush_feedback_buffer(force: bool = False) -> None:
    global _LAST_FLUSH_TS

    to_write: list[dict] = []
    with _FEEDBACK_LOCK:
        if not _FEEDBACK_BUFFER:
            return

        now = time.monotonic()
        flush_due = (
            force
            or len(_FEEDBACK_BUFFER) >= _feedback_buffer_size()
            or (now - _LAST_FLUSH_TS) >= _feedback_flush_interval_seconds()
        )
        if not flush_due:
            return

        to_write = _FEEDBACK_BUFFER[:]
        _FEEDBACK_BUFFER.clear()
        _LAST_FLUSH_TS = now

    log_path = _feedback_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        for payload in to_write:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")


def append_feedback_event(event: FeedbackEventRequest) -> str:
    event_id = str(uuid.uuid4())
    payload = event.model_dump()
    payload["timestamp"] = datetime.now(UTC).isoformat()
    payload["event_id"] = event_id

    with _FEEDBACK_LOCK:
        _FEEDBACK_BUFFER.append(payload)
    _flush_feedback_buffer()

    return event_id


def append_feedback_events(events: list[FeedbackEventRequest]) -> list[str]:
    if not events:
        return []

    event_ids: list[str] = []
    with _FEEDBACK_LOCK:
        for event in events:
            event_id = str(uuid.uuid4())
            payload = event.model_dump()
            payload["timestamp"] = datetime.now(UTC).isoformat()
            payload["event_id"] = event_id
            _FEEDBACK_BUFFER.append(payload)
            event_ids.append(event_id)

    _flush_feedback_buffer()

    return event_ids


def read_feedback_events() -> list[dict]:
    _flush_feedback_buffer(force=True)
    log_path = _feedback_log_path()
    if not log_path.exists():
        return []

    events: list[dict] = []
    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                events.append(row)

    return events


def feedback_stats() -> FeedbackStatsResponse:
    _flush_feedback_buffer(force=True)
    events = read_feedback_events()
    event_type_counts = Counter(str(row.get("event_type", "unknown")) for row in events)

    users = {str(row.get("user_id")) for row in events if row.get("user_id") is not None}
    sessions = {str(row.get("session_id")) for row in events if row.get("session_id") is not None}

    return FeedbackStatsResponse(
        total_events=len(events),
        unique_users=len(users),
        unique_sessions=len(sessions),
        event_type_counts=dict(event_type_counts),
    )
