"""Détection des signaux déclenchant un micro-questionnaire (spec, section 5).

Ce module ne lit PAS directement le store `/feedback/*` existant (dont je
n'ai pas le schéma exact côté code) — il prend une liste d'événements déjà
chargés et les évalue. Adapter `FeedbackEvent`/le point d'appel une fois
branché sur le vrai store de feedback.

Règle générale : jamais plus d'un micro-questionnaire à la fois — un seul
signal, le plus significatif, est retenu par appel à `next_trigger`.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel

from .models import MicroSurveyKind

DISMISSED_THRESHOLD = 3  # nb de "dismissed" sur un même item pour déclencher ban_item
FORMALITY_MISMATCH_THRESHOLD = 3  # nb de rejets liés à la formalité pour déclencher formality_check
MIN_DAYS_BETWEEN_SURVEYS = 14


class FeedbackEvent(BaseModel):
    """Sous-ensemble minimal des champs `/feedback/event` utiles ici."""

    outfit_id: str
    event_type: str  # "impression" | "click" | "selected" | "dismissed"
    item_ids: list[str] = []
    formality_level: Optional[int] = None
    occurred_at: datetime


class SurveyTrigger(BaseModel):
    kind: MicroSurveyKind
    item_id: Optional[str] = None
    reason: str


def _dismissed_item_counts(events: list[FeedbackEvent]) -> Counter:
    counts: Counter = Counter()
    for event in events:
        if event.event_type == "dismissed":
            for item_id in event.item_ids:
                counts[item_id] += 1
    return counts


def _formality_mismatch_count(events: list[FeedbackEvent], target_formality: Optional[int]) -> int:
    if target_formality is None:
        return 0
    mismatches = 0
    for event in events:
        if event.event_type == "dismissed" and event.formality_level is not None:
            if abs(event.formality_level - target_formality) >= 2:
                mismatches += 1
    return mismatches


def next_trigger(
    events: list[FeedbackEvent],
    last_micro_survey_at: Optional[datetime],
    niveau_formalite_prefere: Optional[int],
) -> Optional[SurveyTrigger]:
    """Renvoie au plus un déclenchement, le plus significatif, ou None."""

    if last_micro_survey_at is not None:
        last = last_micro_survey_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last < timedelta(days=MIN_DAYS_BETWEEN_SURVEYS):
            return None

    dismissed_counts = _dismissed_item_counts(events)
    if dismissed_counts:
        item_id, count = dismissed_counts.most_common(1)[0]
        if count >= DISMISSED_THRESHOLD:
            return SurveyTrigger(
                kind=MicroSurveyKind.ban_item,
                item_id=item_id,
                reason=f"{item_id} rejeté {count} fois",
            )

    formality_mismatches = _formality_mismatch_count(events, niveau_formalite_prefere)
    if formality_mismatches >= FORMALITY_MISMATCH_THRESHOLD:
        return SurveyTrigger(
            kind=MicroSurveyKind.formality_check,
            reason=f"{formality_mismatches} rejets liés à la formalité",
        )

    return None
