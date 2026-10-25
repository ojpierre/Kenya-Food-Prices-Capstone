from pathlib import Path
import pandas as pd
import pytest
from src.ingestion import (
    compute_file_checksum,
    ingest_raw_food_prices,
    partition_raw_dataset,
)


def test_compute_file_checksum(tmp_path: Path):
    test_file = tmp_path / "sample.csv"
    test_file.write_text("col1,col2\n1,2\n", encoding="utf-8")
    checksum = compute_file_checksum(test_file)
    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_partition_raw_dataset(tmp_path: Path, sample_raw_df: pd.DataFrame):
    partition_raw_dataset(sample_raw_df, tmp_path)
    part_jan = tmp_path / "year=2024" / "month=01" / "food_prices_batch.csv"
    part_feb = tmp_path / "year=2024" / "month=02" / "food_prices_batch.csv"
    assert part_jan.exists()
    assert part_feb.exists()


def test_ingest_raw_food_prices_benchmark(tmp_path: Path):
    path, meta = ingest_raw_food_prices(output_dir=tmp_path, use_benchmark=True, force_download=True)
    assert path.exists()
    assert meta["rows_ingested"] == 9600
    assert len(meta["checksum_sha256"]) == 64
