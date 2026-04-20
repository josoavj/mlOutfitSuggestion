from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .dataset_contract import ALL_CONTRACTS


PARTITION_TIME_COLUMNS = {
    "users": "updated_at",
    "context_sessions": "timestamp",
    "recommendation_impressions": "shown_at",
    "interactions": "event_time",
}


def to_partition_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.strftime("%Y-%m-%d").fillna("unknown")


def export_table_to_parquet(
    dataset_root: Path,
    output_root: Path,
    table_name: str,
) -> None:
    csv_path = dataset_root / f"{table_name}.csv"
    if not csv_path.exists():
        print(f"[skip] Table absente: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    table_output = output_root / table_name
    table_output.mkdir(parents=True, exist_ok=True)

    partition_col = PARTITION_TIME_COLUMNS.get(table_name)
    try:
        # Trigger an explicit check before writing to fail with a clear message.
        __import__("pyarrow")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pyarrow est requis pour exporter en Parquet. "
            "Installez une version compatible Python (ex: pip install 'pyarrow>=19,<20')."
        ) from exc

    if partition_col and partition_col in df.columns:
        df = df.copy()
        df["partition_date"] = to_partition_date(df[partition_col])
        df.to_parquet(
            table_output,
            index=False,
            engine="pyarrow",
            partition_cols=["partition_date"],
        )
        print(f"[ok] {table_name}: parquet partitionne par partition_date")
        return

    single_file = table_output / f"{table_name}.parquet"
    df.to_parquet(single_file, index=False, engine="pyarrow")
    print(f"[ok] {table_name}: parquet non partitionne -> {single_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporter le dataset CSV en Parquet partitionne")
    parser.add_argument("--dataset-root", type=Path, default=Path("data/dataset"))
    parser.add_argument("--output-root", type=Path, default=Path("data/parquet"))
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)

    for contract in ALL_CONTRACTS:
        export_table_to_parquet(args.dataset_root, args.output_root, contract.table_name)

    print(f"Export termine dans {args.output_root}")


if __name__ == "__main__":
    main()
