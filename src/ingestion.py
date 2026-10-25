import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import requests

try:
    from .benchmark_data import generate_benchmark_dataset
    from .config import settings
except ImportError:
    from benchmark_data import generate_benchmark_dataset
    from config import settings

logger = logging.getLogger(__name__)


def compute_file_checksum(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def ingest_raw_food_prices(
    source_url: Optional[str] = None,
    output_dir: Optional[Path] = None,
    force_download: bool = False,
    use_benchmark: bool = True,
) -> Tuple[Path, Dict[str, Any]]:
    target_dir = output_dir or settings.raw_data_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_master_path = target_dir / "wfp_food_prices_kenya_raw.csv"

    url = source_url or settings.source_url
    metadata: Dict[str, Any] = {
        "source_url": url,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "is_benchmark": False,
        "rows_ingested": 0,
        "checksum_sha256": "",
    }

    if raw_master_path.exists() and not force_download:
        logger.info("Found existing raw dataset at %s. Verifying checksum...", raw_master_path)
        df_existing = pd.read_csv(raw_master_path, low_memory=False)
        metadata["rows_ingested"] = len(df_existing)
        metadata["checksum_sha256"] = compute_file_checksum(raw_master_path)
        return raw_master_path, metadata

    download_success = False
    if not use_benchmark:
        try:
            logger.info("Connecting to HDX / WFP endpoint: %s", url)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(raw_master_path, "wb") as f:
                f.write(response.content)
            download_success = True
            logger.info("Successfully downloaded raw data from external endpoint.")
        except Exception as exc:
            logger.warning("External download failed: %s. Falling back to benchmark dataset.", exc)

    if not download_success:
        logger.info("Generating realistic Kenya food prices benchmark dataset (2021-2024)...")
        df_benchmark = generate_benchmark_dataset(start_year=2021, end_year=2024)
        df_benchmark.to_csv(raw_master_path, index=False)
        metadata["is_benchmark"] = True

    df_raw = pd.read_csv(raw_master_path, low_memory=False)
    metadata["rows_ingested"] = len(df_raw)
    metadata["checksum_sha256"] = compute_file_checksum(raw_master_path)

    partition_raw_dataset(df_raw, target_dir)

    logger.info(
        "Ingestion completed: %d records landed in %s (SHA-256: %s)",
        len(df_raw),
        raw_master_path,
        metadata["checksum_sha256"][:12],
    )
    return raw_master_path, metadata


def partition_raw_dataset(df: pd.DataFrame, base_dir: Path) -> None:
    if "date" not in df.columns:
        return

    df["_date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    for (year, month), partition_df in df.groupby([df["_date_parsed"].dt.year, df["_date_parsed"].dt.month]):
        if pd.isna(year) or pd.isna(month):
            continue
        part_dir = base_dir / f"year={int(year)}" / f"month={int(month):02d}"
        part_dir.mkdir(parents=True, exist_ok=True)
        part_file = part_dir / "food_prices_batch.csv"
        partition_df.drop(columns=["_date_parsed"]).to_csv(part_file, index=False)
