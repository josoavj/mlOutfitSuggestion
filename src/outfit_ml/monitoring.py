"""Suivi des performances et de l'historique du modèle, par période.

Trois sources, une seule vue (jour / semaine / mois) :
  - training_runs : un enregistrement par entraînement (métriques, données, modèle archivé)
  - inference_log : un enregistrement par requête de recommandation
                    (étalement des scores, replis heuristiques, latence, répétition)
  - feedback JSONL : impressions / clics / sélections, agrégés par période

Les écritures côté requête (log_inference) sont « best effort » : un problème de
monitoring ne doit jamais faire échouer une recommandation.

Placer ce fichier dans src/outfit_ml/monitoring.py.
Rapport en terminal : python -m src.outfit_ml.monitoring --granularity week --days 90
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import sqlite3
import statistics
import subprocess
import time
import uuid
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("MONITORING_DB", "data/monitoring.db"))
ARCHIVE_DIR = Path(os.getenv("MODEL_ARCHIVE_DIR", "models/archive"))
FEEDBACK_LOG = Path(os.getenv("FEEDBACK_LOG", "data/feedback/events.jsonl"))

# Semaine ISO (lundi → dimanche), identique côté écriture et lecture.
PERIOD_FORMATS = {"day": "%Y-%m-%d", "week": "%G-W%V", "month": "%Y-%m"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS training_runs (
    run_id        TEXT PRIMARY KEY,
    ts            TEXT NOT NULL,
    algo          TEXT,
    data_source   TEXT,
    n_samples     INTEGER,
    positive_rate REAL,
    split_mode    TEXT,
    metrics       TEXT,
    params        TEXT,
    dataset_hash  TEXT,
    git_commit    TEXT,
    model_path    TEXT,
    is_current    INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS inference_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    request_id    TEXT,
    user_id       TEXT,
    model_run_id  TEXT,
    n_candidates  INTEGER,
    n_suggestions INTEGER,
    score_min     REAL,
    score_max     REAL,
    score_std     REAL,
    ml_fallbacks  INTEGER,
    latency_ms    REAL,
    outfit_keys   TEXT,
    top_keys      TEXT
);
CREATE INDEX IF NOT EXISTS idx_inference_ts ON inference_log(ts);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # plusieurs workers : lectures/écritures concurrentes
    conn.executescript(SCHEMA)
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _bucket(ts: datetime, granularity: str) -> str:
    return ts.strftime(PERIOD_FORMATS[granularity])


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3, check=True,
        )
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Entraînements
# ---------------------------------------------------------------------------

def log_training_run(
    *,
    algo: str,
    data_source: str,
    n_samples: int,
    positive_rate: float | None,
    split_mode: str,
    metrics: dict,
    model_path: Path,
    params: dict | None = None,
    dataset_hash: str | None = None,
) -> str:
    """Enregistre un entraînement, archive le modèle produit et le marque « en service »."""
    run_id = _now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]

    archived: Path | None = None
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archived = ARCHIVE_DIR / f"outfit_ranker_{run_id}.joblib"
        shutil.copy2(model_path, archived)
    except OSError:
        logger.exception("Archivage du modèle impossible")
        archived = None

    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE training_runs SET is_current = 0")
        conn.execute(
            """INSERT INTO training_runs
               (run_id, ts, algo, data_source, n_samples, positive_rate, split_mode,
                metrics, params, dataset_hash, git_commit, model_path, is_current)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                run_id, _now().isoformat(), algo, data_source, int(n_samples), positive_rate,
                split_mode, json.dumps(metrics, default=str), json.dumps(params or {}, default=str),
                dataset_hash, _git_commit(), str(archived or model_path),
            ),
        )
    return run_id


_run_cache: tuple[float, str | None] = (0.0, None)


def current_run_id() -> str | None:
    """Identifiant de l'entraînement en service (mis en cache 60 s)."""
    global _run_cache
    if time.monotonic() - _run_cache[0] < 60:
        return _run_cache[1]
    run_id: str | None = None
    try:
        with closing(_connect()) as conn:
            row = conn.execute("SELECT run_id FROM training_runs WHERE is_current = 1").fetchone()
        run_id = row["run_id"] if row else None
    except sqlite3.Error:
        logger.exception("Lecture du run courant impossible")
    _run_cache = (time.monotonic(), run_id)
    return run_id


def training_history(limit: int = 50) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM training_runs ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    runs = []
    for r in rows:
        run = dict(r)
        run["metrics"] = json.loads(run["metrics"] or "{}")
        run["params"] = json.loads(run["params"] or "{}")
        run["is_current"] = bool(run["is_current"])
        runs.append(run)
    return runs


# ---------------------------------------------------------------------------
# Inférence
# ---------------------------------------------------------------------------

def summarize_scores(scores: list[float]) -> dict:
    """Étalement des scores d'un lot de candidats (un écart-type quasi nul = classement plat)."""
    clean = [s for s in scores if s is not None and math.isfinite(s)]
    if not clean:
        return {"score_min": None, "score_max": None, "score_std": None}
    return {
        "score_min": min(clean),
        "score_max": max(clean),
        "score_std": statistics.pstdev(clean) if len(clean) > 1 else 0.0,
    }


def log_inference(
    *,
    request_id: str | None,
    user_id: str | None,
    n_candidates: int,
    n_suggestions: int,
    score_summary: dict,
    ml_fallbacks: int,
    latency_ms: float,
    outfit_keys: list[str],
    top_keys: list[str],
) -> None:
    """Journalise une requête de recommandation. Ne lève jamais."""
    try:
        with closing(_connect()) as conn, conn:
            conn.execute(
                """INSERT INTO inference_log
                   (ts, request_id, user_id, model_run_id, n_candidates, n_suggestions,
                    score_min, score_max, score_std, ml_fallbacks, latency_ms, outfit_keys, top_keys)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now().isoformat(), request_id, user_id, current_run_id(),
                    n_candidates, n_suggestions,
                    score_summary.get("score_min"), score_summary.get("score_max"),
                    score_summary.get("score_std"), ml_fallbacks, latency_ms,
                    json.dumps(outfit_keys), json.dumps(top_keys),
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception("Journalisation de l'inférence impossible")


def inference_stats(granularity: str = "week", days: int = 90) -> list[dict]:
    cutoff = (_now() - timedelta(days=days)).isoformat()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM inference_log WHERE ts >= ? ORDER BY ts", (cutoff,)
        ).fetchall()

    buckets: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        ts = _parse_ts(r["ts"])
        if ts:
            buckets[_bucket(ts, granularity)].append(r)

    out = []
    for period in sorted(buckets):
        rs = buckets[period]
        candidates = sum(r["n_candidates"] or 0 for r in rs)
        fallbacks = sum(r["ml_fallbacks"] or 0 for r in rs)
        stds = [r["score_std"] for r in rs if r["score_std"] is not None]
        ranges = [
            r["score_max"] - r["score_min"]
            for r in rs if r["score_max"] is not None and r["score_min"] is not None
        ]
        latencies = [r["latency_ms"] for r in rs if r["latency_ms"] is not None]

        # Répétition : part des suggestions déjà montrées au même utilisateur dans la période.
        outfits_by_user: dict[str, list[str]] = defaultdict(list)
        tops_by_user: dict[str, set[str]] = defaultdict(set)
        for r in rs:
            user = r["user_id"] or "?"
            outfits_by_user[user].extend(json.loads(r["outfit_keys"] or "[]"))
            tops_by_user[user].update(json.loads(r["top_keys"] or "[]"))
        shown = sum(len(v) for v in outfits_by_user.values())
        distinct = sum(len(set(v)) for v in outfits_by_user.values())
        n_users = max(len(outfits_by_user), 1)

        out.append({
            "period": period,
            "requests": len(rs),
            "empty_rate": sum(1 for r in rs if not r["n_suggestions"]) / len(rs),
            "fallback_rate": (fallbacks / candidates) if candidates else None,
            "score_std": statistics.fmean(stds) if stds else None,
            "score_range": statistics.fmean(ranges) if ranges else None,
            "latency_avg_ms": statistics.fmean(latencies) if latencies else None,
            "latency_p95_ms": _p95(latencies),
            "repeat_rate": (1 - distinct / shown) if shown else None,
            "distinct_outfits_per_user": distinct / n_users,
            "distinct_tops_per_user": sum(len(v) for v in tops_by_user.values()) / n_users,
            "model_runs": sorted({r["model_run_id"] for r in rs if r["model_run_id"]}),
        })
    return out


# ---------------------------------------------------------------------------
# Feedback (lecture du JSONL existant)
# ---------------------------------------------------------------------------

def feedback_stats(
    granularity: str = "week", days: int = 90, path: Path | None = None
) -> list[dict]:
    path = path or FEEDBACK_LOG
    if not path.exists():
        return []
    cutoff = _now() - timedelta(days=days)
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            ts = _parse_ts(event.get("timestamp") or event.get("ts") or event.get("created_at"))
            if ts is None or ts < cutoff:
                continue
            bucket = buckets[_bucket(ts, granularity)]
            kind = event.get("event_type")
            bucket[str(kind)] += 1
            if kind == "selected":
                rank = (event.get("metadata") or {}).get("rank_position")
                if rank == 0:
                    bucket["selected_rank0"] += 1

    out = []
    for period in sorted(buckets):
        b = buckets[period]
        impressions, selected = b["impression"], b["selected"]
        out.append({
            "period": period,
            "impressions": impressions,
            "selected": selected,
            "clicks": b["click"],
            "dismissed": b["dismissed"],
            "selection_rate": selected / impressions if impressions else None,
            "click_rate": b["click"] / impressions if impressions else None,
            "dismiss_rate": b["dismissed"] / impressions if impressions else None,
            "rank1_share": b["selected_rank0"] / selected if selected else None,
        })
    return out


# ---------------------------------------------------------------------------
# Vue consolidée
# ---------------------------------------------------------------------------

def history_payload(granularity: str = "week", days: int = 90, feedback_path: Path | None = None) -> dict:
    if granularity not in PERIOD_FORMATS:
        raise ValueError(f"granularity doit être l'une de {list(PERIOD_FORMATS)}")
    return {
        "granularity": granularity,
        "days": days,
        "generated_at": _now().isoformat(),
        "current_run_id": current_run_id(),
        "training_runs": training_history(),
        "inference": inference_stats(granularity, days),
        "feedback": feedback_stats(granularity, days, feedback_path),
    }


# ---------------------------------------------------------------------------
# Rapport en terminal
# ---------------------------------------------------------------------------

def _fmt(value) -> str:
    if value is None:
        return "–"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return ",".join(value)
    return str(value)


def _print_table(title: str, rows: list[dict], columns: list[str]) -> None:
    print(f"\n{title}")
    if not rows:
        print("  (aucune donnée)")
        return
    widths = [max(len(c), *(len(_fmt(r.get(c))) for r in rows)) for c in columns]
    print("  " + "  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    for r in rows:
        print("  " + "  ".join(_fmt(r.get(c)).ljust(w) for c, w in zip(columns, widths)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rapport de suivi du modèle")
    parser.add_argument("--granularity", choices=list(PERIOD_FORMATS), default="week")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    payload = history_payload(args.granularity, args.days)
    runs = [
        {"run_id": r["run_id"], "algo": r["algo"], "données": r["data_source"],
         "n": r["n_samples"], "positifs": r["positive_rate"],
         "roc_auc": r["metrics"].get("roc_auc"), "f1": r["metrics"].get("f1"),
         "en_service": "oui" if r["is_current"] else ""}
        for r in payload["training_runs"]
    ]
    _print_table("Entraînements", runs,
                 ["run_id", "algo", "données", "n", "positifs", "roc_auc", "f1", "en_service"])
    _print_table("Inférence", payload["inference"],
                 ["period", "requests", "empty_rate", "fallback_rate", "score_std",
                  "score_range", "repeat_rate", "distinct_tops_per_user", "latency_p95_ms"])
    _print_table("Feedback", payload["feedback"],
                 ["period", "impressions", "selected", "selection_rate", "click_rate",
                  "dismiss_rate", "rank1_share"])


if __name__ == "__main__":
    main()
