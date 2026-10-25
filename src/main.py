import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from .config import settings
    from .data_quality import DataQualityEngine
    from .ingestion import ingest_raw_food_prices
    from .transformation import clean_and_normalize_food_prices
    from .warehouse import get_engine, load_fact_table
except ImportError:
    from config import settings
    from data_quality import DataQualityEngine
    from ingestion import ingest_raw_food_prices
    from transformation import clean_and_normalize_food_prices
    from warehouse import get_engine, load_fact_table

logger = logging.getLogger("kenya_food_prices_etl")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_pipeline(
    database_url: Optional[str] = None,
    force_download: bool = False,
    use_benchmark: bool = True,
    mode: str = "append",
) -> Dict[str, Any]:
    start_time = time.time()
    batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    logger.info("=================================================================")
    logger.info("Starting Kenya Food Prices & Inflation Platform ETL Pipeline")
    logger.info("Batch ID: %s | Mode: %s | Benchmark: %s", batch_id, mode, use_benchmark)
    logger.info("=================================================================")

    logger.info("[Stage 1/4] Ingesting raw food price observations...")
    raw_path, meta = ingest_raw_food_prices(
        source_url=settings.source_url if not use_benchmark else None,
        use_benchmark=use_benchmark,
    )
    raw_count = meta.get("rows_ingested", 0)

    logger.info("[Stage 2/4] Normalising units, cleaning currency, and calculating inflation...")
    cleaned_df = clean_and_normalize_food_prices(raw_path)
    cleaned_count = len(cleaned_df)

    logger.info("[Stage 3/4] Populating dimensional warehouse and loading fact table...")
    engine = get_engine(database_url)
    facts_loaded = load_fact_table(cleaned_df, engine, if_exists=mode)

    logger.info("[Stage 4/4] Executing automated data quality assertions...")
    dq_engine = DataQualityEngine(engine)
    all_passed, dq_results = dq_engine.run_all_validation_checks()

    duration = round(time.time() - start_time, 2)

    dq_engine.record_lineage(
        batch_id=batch_id,
        source_uri=meta.get("source_url", settings.source_url),
        raw_count=raw_count,
        cleaned_count=cleaned_count,
        fact_count=facts_loaded,
        duration_sec=duration,
        dq_results=dq_results,
    )

    logger.info("=================================================================")
    logger.info("Pipeline Execution Completed Successfully in %.2f seconds", duration)
    logger.info(" - Raw Observations Landed: %d", raw_count)
    logger.info(" - Cleaned Records Staged:  %d", cleaned_count)
    logger.info(" - Fact Records Loaded:     %d", facts_loaded)
    logger.info(" - Data Quality Status:     %s (%d/%d checks passed)",
                "PASSED" if all_passed else "WARNING/FAILED",
                sum(1 for r in dq_results if r["passed"]),
                len(dq_results))
    logger.info("=================================================================")

    summary = {
        "batch_id": batch_id,
        "mode": mode,
        "raw_rows": raw_count,
        "cleaned_rows": cleaned_count,
        "fact_rows": facts_loaded,
        "dq_status": "PASSED" if all_passed else "FAILED",
        "dq_passed_checks": sum(1 for r in dq_results if r["passed"]),
        "dq_total_checks": len(dq_results),
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kenya Food Prices & Inflation Platform - End-to-End ETL Pipeline"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL override (PostgreSQL or SQLite).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion and overwrite of existing raw landing files.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt live extraction from external HDX endpoint instead of benchmark data.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["append", "replace"],
        default="append",
        help="Warehouse fact table write mode: append or replace (default: append).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity level (default: INFO).",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)

    setup_logging(parsed.log_level)

    try:
        summary = run_pipeline(
            database_url=parsed.db_url,
            force_download=parsed.force,
            use_benchmark=not parsed.live,
            mode=parsed.mode,
        )
        return 0 if summary.get("fact_rows", 0) > 0 else 1
    except Exception as exc:
        logger.exception("Pipeline execution failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
