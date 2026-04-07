from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split

from .data import load_catalog, synthetic_training_pairs


CATEGORICAL = ["gender", "body_shape", "occasion", "weather", "outfit_id"]
NUMERIC = [
    "age",
    "height_cm",
    "style_match",
    "occasion_match",
    "weather_match",
    "shape_match",
    "gender_match",
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
        raise ValueError(f"Modele inconnu: {model_name}")

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
    return {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


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
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    data = synthetic_training_pairs(catalog, n_samples=args.samples)

    X = data.drop(columns=["label"])
    y = data["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

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
        raise RuntimeError("Aucun modele n'a pu etre entraine")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, args.output)

    metadata = {
        "best_model": best_name,
        "metrics": best_metrics,
        "samples": int(args.samples),
    }
    with args.metrics_output.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Modele entraine ({best_name}) et sauvegarde dans {args.output}")
    print(f"Metriques sauvegardees dans {args.metrics_output}")
    print(f"ROC-AUC={best_metrics['roc_auc']:.4f} AP={best_metrics['average_precision']:.4f}")


if __name__ == "__main__":
    main()
