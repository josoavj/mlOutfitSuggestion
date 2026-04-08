from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .schemas import FeedbackEventRequest, FeedbackStatsResponse


def _feedback_log_path() -> Path:
    raw_path = os.getenv("FEEDBACK_LOG_PATH", "data/feedback/events.jsonl").strip()
    return Path(raw_path)


def append_feedback_event(event: FeedbackEventRequest) -> str:
    event_id = str(uuid.uuid4())
    payload = event.model_dump()

    if payload.get("timestamp") is None:
        payload["timestamp"] = datetime.now(UTC).isoformat()
    else:
        payload["timestamp"] = event.timestamp.isoformat()

    payload["event_id"] = event_id

    log_path = _feedback_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")

    return event_id


def append_feedback_events(events: list[FeedbackEventRequest]) -> list[str]:
    if not events:
        return []

    log_path = _feedback_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    event_ids: list[str] = []
    with log_path.open("a", encoding="utf-8") as file:
        for event in events:
            event_id = str(uuid.uuid4())
            payload = event.model_dump()

            if payload.get("timestamp") is None:
                payload["timestamp"] = datetime.now(UTC).isoformat()
            else:
                payload["timestamp"] = event.timestamp.isoformat()

            payload["event_id"] = event_id
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
            event_ids.append(event_id)

    return event_ids


def read_feedback_events() -> list[dict]:
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
