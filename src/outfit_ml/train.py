from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split

from .data import load_catalog, real_training_pairs_from_feedback, synthetic_training_pairs


CATEGORICAL = [
    "gender",
    "body_shape",
    "occasion",
    "weather",
    "clothing_size",
    "top_size",
    "bottom_size",
    "shoe_bucket",
    "outfit_id",
]
NUMERIC = [
    "age",
    "height_cm",
    "style_match",
    "occasion_match",
    "weather_match",
    "shape_match",
    "gender_match",
    "clothing_size_match",
    "top_size_match",
    "bottom_size_match",
    "shoe_size_match",
    "pref_classic",
    "pref_minimalist",
    "pref_casual",
    "pref_sport",
    "pref_elegant",
    "pref_practical",
    "outfit_style_classic",
    "outfit_style_minimalist",
    "outfit_style_casual",
    "outfit_style_sport",
    "outfit_style_elegant",
    "outfit_style_practical",
]


def build_pipeline(model_name: str) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL,
            ),
            ("numeric", "passthrough", NUMERIC),
        ]
    )

    candidates = {
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            max_depth=14,
            random_state=42,
            class_weight="balanced_subsample",
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=450,
            max_depth=None,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        ),
    }

    if model_name not in candidates:
        raise ValueError(f"Modèle inconnu : {model_name}")

    model = candidates[model_name]

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("model", model),
        ]
    )


def evaluate_pipeline(pipeline: Pipeline, X_test, y_test) -> dict[str, float]:
    probabilities = pipeline.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        predictions,
        average="binary",
        zero_division=0,
    )
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }

    if "session_id" in X_test.columns:
        ranking_df = pd.DataFrame(
            {
                "session_id": X_test["session_id"].astype(str),
                "label": y_test.astype(int),
                "score": probabilities,
            }
        )
        metrics.update(compute_ranking_metrics(ranking_df, k=3))

    return metrics


def compute_ranking_metrics(ranking_df: pd.DataFrame, k: int = 3) -> dict[str, float]:
    precision_scores: list[float] = []
    recall_scores: list[float] = []
    ndcg_scores: list[float] = []

    for _, group in ranking_df.groupby("session_id"):
        sorted_group = group.sort_values("score", ascending=False)
        topk = sorted_group.head(k)

        positives_total = int(group["label"].sum())
        positives_topk = int(topk["label"].sum())

        precision_scores.append(positives_topk / max(k, 1))
        recall_scores.append(positives_topk / max(positives_total, 1))

        gains = topk["label"].to_numpy(dtype=float)
        discounts = np.log2(np.arange(2, len(gains) + 2))
        dcg = float(np.sum(gains / discounts)) if len(gains) else 0.0

        ideal_gains = np.sort(group["label"].to_numpy(dtype=float))[::-1][:k]
        ideal_discounts = np.log2(np.arange(2, len(ideal_gains) + 2))
        idcg = float(np.sum(ideal_gains / ideal_discounts)) if len(ideal_gains) else 0.0
        ndcg_scores.append(float(dcg / idcg) if idcg > 0 else 0.0)

    return {
        f"precision_at_{k}": float(np.mean(precision_scores)) if precision_scores else 0.0,
        f"recall_at_{k}": float(np.mean(recall_scores)) if recall_scores else 0.0,
        f"ndcg_at_{k}": float(np.mean(ndcg_scores)) if ndcg_scores else 0.0,
    }


def split_dataset(data: pd.DataFrame, split_mode: str):
    y = data["label"].astype(int)

    if split_mode == "time" and "event_ts" in data.columns:
        ordered = data.copy()
        ordered["event_ts"] = pd.to_datetime(ordered["event_ts"], errors="coerce")
        ordered = ordered.sort_values("event_ts")
        split_idx = max(int(len(ordered) * 0.8), 1)
        train_df = ordered.iloc[:split_idx]
        test_df = ordered.iloc[split_idx:]

        X_train = train_df.drop(columns=["label"])
        y_train = train_df["label"].astype(int)
        X_test = test_df.drop(columns=["label"])
        y_test = test_df["label"].astype(int)
        return X_train, X_test, y_train, y_test

    X = data.drop(columns=["label"])
    return train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=4000)
    parser.add_argument("--catalog", type=Path, default=Path("configs/outfit_catalog.json"))
    parser.add_argument("--output", type=Path, default=Path("models/outfit_ranker.joblib"))
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("models/outfit_ranker_metrics.json"),
    )
    parser.add_argument(
        "--model-candidates",
        nargs="+",
        default=["random_forest", "extra_trees"],
    )
    parser.add_argument(
        "--real-feedback-log",
        type=Path,
        default=Path("data/feedback/events.jsonl"),
    )
    parser.add_argument("--prefer-real-data", action="store_true")
    parser.add_argument("--min-real-samples", type=int, default=200)
    parser.add_argument(
        "--split-mode",
        choices=["random", "time"],
        default="random",
    )
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    data_source = "synthetic"

    if args.prefer_real_data:
        real_data = real_training_pairs_from_feedback(catalog, args.real_feedback_log)
        if len(real_data) >= args.min_real_samples and real_data["label"].nunique() > 1:
            data = real_data
            data_source = "real_feedback"
        else:
            data = synthetic_training_pairs(catalog, n_samples=args.samples)
    else:
        data = synthetic_training_pairs(catalog, n_samples=args.samples)

    X_train, X_test, y_train, y_test = split_dataset(data, split_mode=args.split_mode)

    best_name: str | None = None
    best_pipeline: Pipeline | None = None
    best_metrics: dict[str, float] | None = None

    for model_name in args.model_candidates:
        pipeline = build_pipeline(model_name)
        pipeline.fit(X_train, y_train)
        metrics = evaluate_pipeline(pipeline, X_test, y_test)

        if best_metrics is None or metrics["roc_auc"] > best_metrics["roc_auc"]:
            best_name = model_name
            best_pipeline = pipeline
            best_metrics = metrics

    if best_pipeline is None or best_name is None or best_metrics is None:
        raise RuntimeError("Aucun modèle n'a pu être entraîné")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, args.output)

    metadata = {
        "best_model": best_name,
        "metrics": best_metrics,
        "samples": int(len(data)),
        "data_source": data_source,
        "split_mode": args.split_mode,
    }
    with args.metrics_output.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Modèle entraîné ({best_name}) et sauvegardé dans {args.output}")
    print(f"Métriques sauvegardées dans {args.metrics_output}")
    print(f"Lignes d'entraînement : {len(data)}")
    print(f"ROC-AUC={best_metrics['roc_auc']:.4f} AP={best_metrics['average_precision']:.4f}")


if __name__ == "__main__":
    main()
