from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from .dataset_contract import (
    ALL_CONTRACTS,
    ALLOWED_BODY_SHAPES,
    ALLOWED_CLOTHING_SIZES,
    ALLOWED_EVENT_TYPES,
    ALLOWED_GENDERS,
    ALLOWED_OCCASIONS,
    ALLOWED_WEATHER_BUCKETS,
    TableContract,
)


@dataclass
class TableValidationResult:
    table_name: str
    file_path: str
    row_count: int = 0
    missing_columns: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    null_rate_by_column: dict[str, float] = field(default_factory=dict)
    invalid_values: dict[str, int] = field(default_factory=dict)
    passed: bool = True


@dataclass
class ValidationReport:
    dataset_root: str
    table_results: list[TableValidationResult]
    global_passed: bool


def parse_set_cell(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, float) and pd.isna(value):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {part.strip().lower() for part in text.split("|") if part.strip()}


def invalid_value_count(series: pd.Series, allowed: set[str]) -> int:
    normalized = series.fillna("unknown").astype(str).str.strip().str.lower()
    return int((~normalized.isin(allowed)).sum())


def validate_table(file_path: Path, contract: TableContract) -> TableValidationResult:
    result = TableValidationResult(table_name=contract.table_name, file_path=str(file_path))

    if not file_path.exists():
        result.passed = False
        result.missing_columns = list(contract.required_columns)
        return result

    df = pd.read_csv(file_path)
    result.row_count = int(len(df))

    columns = set(df.columns)
    required = set(contract.required_columns)
    missing = sorted(required - columns)
    if missing:
        result.missing_columns = missing
        result.passed = False
        return result

    if contract.primary_key_hint:
        result.duplicate_count = int(df.duplicated(list(contract.primary_key_hint)).sum())

    for column in contract.required_columns:
        result.null_rate_by_column[column] = float(df[column].isna().mean())

    if contract.table_name == "users":
        result.invalid_values["gender"] = invalid_value_count(df["gender"], ALLOWED_GENDERS)
        result.invalid_values["body_shape"] = invalid_value_count(df["body_shape"], ALLOWED_BODY_SHAPES)
        result.invalid_values["clothing_size"] = invalid_value_count(
            df["clothing_size"], ALLOWED_CLOTHING_SIZES
        )
        result.invalid_values["top_size"] = invalid_value_count(df["top_size"], ALLOWED_CLOTHING_SIZES)
        result.invalid_values["bottom_size"] = invalid_value_count(
            df["bottom_size"], ALLOWED_CLOTHING_SIZES
        )
    elif contract.table_name == "context_sessions":
        result.invalid_values["weather_bucket"] = invalid_value_count(
            df["weather_bucket"], ALLOWED_WEATHER_BUCKETS
        )
        invalid_occasion = 0
        for value in df["agenda_labels"]:
            tags = parse_set_cell(value)
            if not tags:
                continue
            if not tags.issubset(ALLOWED_OCCASIONS):
                invalid_occasion += 1
        result.invalid_values["agenda_labels"] = invalid_occasion
    elif contract.table_name == "interactions":
        result.invalid_values["event_type"] = invalid_value_count(df["event_type"], ALLOWED_EVENT_TYPES)

    any_invalid = any(count > 0 for count in result.invalid_values.values())
    too_many_nulls = any(rate > 0.05 for rate in result.null_rate_by_column.values())
    has_duplicates = result.duplicate_count > 0

    result.passed = not (any_invalid or too_many_nulls or has_duplicates)
    return result


def build_report(dataset_root: Path) -> ValidationReport:
    table_results: list[TableValidationResult] = []
    for contract in ALL_CONTRACTS:
        file_path = dataset_root / f"{contract.table_name}.csv"
        table_results.append(validate_table(file_path, contract))

    global_passed = all(item.passed for item in table_results)
    return ValidationReport(
        dataset_root=str(dataset_root),
        table_results=table_results,
        global_passed=global_passed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validation du dataset de recommandations")
    parser.add_argument("--dataset-root", type=Path, default=Path("data/dataset"))
    parser.add_argument("--report-output", type=Path, default=Path("data/quality/validation_report.json"))
    args = parser.parse_args()

    report = build_report(args.dataset_root)

    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    with args.report_output.open("w", encoding="utf-8") as file:
        json.dump(asdict(report), file, indent=2)

    status = "PASS" if report.global_passed else "FAIL"
    print(f"Validation dataset: {status}")
    print(f"Rapport: {args.report_output}")


if __name__ == "__main__":
    main()
