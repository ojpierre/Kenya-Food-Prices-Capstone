import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)


class DataQualityEngine:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._ensure_lineage_table()

    def _ensure_lineage_table(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS etl_batch_lineage (
            batch_id VARCHAR(50) PRIMARY KEY,
            source_uri VARCHAR(255) NOT NULL,
            update_frequency VARCHAR(50) NOT NULL,
            pipeline_stage VARCHAR(50) NOT NULL,
            raw_row_count INTEGER NOT NULL,
            cleaned_row_count INTEGER NOT NULL,
            fact_rows_loaded INTEGER NOT NULL,
            dq_checks_total INTEGER NOT NULL,
            dq_checks_passed INTEGER NOT NULL,
            dq_status VARCHAR(20) NOT NULL,
            dq_details TEXT,
            execution_duration_sec DECIMAL(6, 2),
            recorded_at TIMESTAMP NOT NULL
        );
        """
        with self.engine.begin() as conn:
            conn.execute(text(ddl))

    def run_all_validation_checks(self) -> Tuple[bool, List[Dict[str, Any]]]:
        results: List[Dict[str, Any]] = []

        with self.engine.connect() as conn:
            # Check 1: Completeness - Fact Table Non-Empty
            fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_food_price")).scalar() or 0
            results.append({
                "check_name": "Fact Table Non-Empty Assertion",
                "table": "fact_food_price",
                "passed": fact_count > 0,
                "details": f"Fact table contains {fact_count} rows.",
            })

            # Check 2: Uniqueness - Primary Keys in Dimensions
            comm_dups = conn.execute(text("SELECT COUNT(*) - COUNT(DISTINCT commodity_key) FROM dim_commodity")).scalar() or 0
            results.append({
                "check_name": "Commodity Dimension Key Uniqueness",
                "table": "dim_commodity",
                "passed": comm_dups == 0,
                "details": f"Duplicate commodity keys detected: {comm_dups}",
            })

            mkt_dups = conn.execute(text("SELECT COUNT(*) - COUNT(DISTINCT market_key) FROM dim_county_market")).scalar() or 0
            results.append({
                "check_name": "Market Dimension Key Uniqueness",
                "table": "dim_county_market",
                "passed": mkt_dups == 0,
                "details": f"Duplicate market keys detected: {mkt_dups}",
            })

            # Check 3: Validity - Price Boundary Assertion (Prices > 0 and < 50,000 KES)
            invalid_prices = conn.execute(text(
                "SELECT COUNT(*) FROM fact_food_price WHERE normalized_price_kes <= 0 OR normalized_price_kes > 50000"
            )).scalar() or 0
            results.append({
                "check_name": "Positive & Realistic Unit Price Range Check",
                "table": "fact_food_price",
                "passed": invalid_prices == 0,
                "details": f"Out-of-range prices (<0 or >50k KES): {invalid_prices}",
            })

            # Check 4: Referential Integrity - Orphan Checks
            orphan_comm = conn.execute(text("""
                SELECT COUNT(*) FROM fact_food_price f
                LEFT JOIN dim_commodity c ON f.commodity_key = c.commodity_key
                WHERE c.commodity_key IS NULL
            """)).scalar() or 0
            results.append({
                "check_name": "Commodity Referential Integrity",
                "table": "fact_food_price -> dim_commodity",
                "passed": orphan_comm == 0,
                "details": f"Orphan fact records without commodity match: {orphan_comm}",
            })

            orphan_mkt = conn.execute(text("""
                SELECT COUNT(*) FROM fact_food_price f
                LEFT JOIN dim_county_market m ON f.market_key = m.market_key
                WHERE m.market_key IS NULL
            """)).scalar() or 0
            results.append({
                "check_name": "Market Referential Integrity",
                "table": "fact_food_price -> dim_county_market",
                "passed": orphan_mkt == 0,
                "details": f"Orphan fact records without market match: {orphan_mkt}",
            })

            orphan_date = conn.execute(text("""
                SELECT COUNT(*) FROM fact_food_price f
                LEFT JOIN dim_date d ON f.date_key = d.date_key
                WHERE d.date_key IS NULL
            """)).scalar() or 0
            results.append({
                "check_name": "Date Referential Integrity",
                "table": "fact_food_price -> dim_date",
                "passed": orphan_date == 0,
                "details": f"Orphan fact records without date match: {orphan_date}",
            })

            # Check 5: Temporal Sanity - No Future Observations
            current_date_int = int(datetime.now().strftime("%Y%m%d"))
            future_dates = conn.execute(text(
                f"SELECT COUNT(*) FROM fact_food_price WHERE date_key > {current_date_int}"
            )).scalar() or 0
            results.append({
                "check_name": "No Future Date Observations",
                "table": "fact_food_price",
                "passed": future_dates == 0,
                "details": f"Future date records detected: {future_dates}",
            })

        all_passed = all(r["passed"] for r in results)
        logger.info(
            "Data Quality Suite executed: %d/%d checks passed.",
            sum(1 for r in results if r["passed"]),
            len(results),
        )
        return all_passed, results

    def record_lineage(
        self,
        batch_id: str,
        source_uri: str,
        raw_count: int,
        cleaned_count: int,
        fact_count: int,
        duration_sec: float,
        dq_results: List[Dict[str, Any]],
    ) -> None:
        total_checks = len(dq_results)
        passed_checks = sum(1 for r in dq_results if r["passed"])
        dq_status = "PASSED" if passed_checks == total_checks else "FAILED"

        insert_sql = """
        INSERT INTO etl_batch_lineage (
            batch_id, source_uri, update_frequency, pipeline_stage,
            raw_row_count, cleaned_row_count, fact_rows_loaded,
            dq_checks_total, dq_checks_passed, dq_status, dq_details,
            execution_duration_sec, recorded_at
        ) VALUES (
            :batch_id, :source_uri, 'Monthly', 'Full_End_to_End',
            :raw_count, :cleaned_count, :fact_count,
            :total_checks, :passed_checks, :dq_status, :dq_details,
            :duration_sec, :recorded_at
        )
        """
        params = {
            "batch_id": batch_id,
            "source_uri": source_uri,
            "raw_count": raw_count,
            "cleaned_count": cleaned_count,
            "fact_count": fact_count,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "dq_status": dq_status,
            "dq_details": json.dumps(dq_results),
            "duration_sec": round(duration_sec, 2),
            "recorded_at": datetime.now(timezone.utc),
        }
        with self.engine.begin() as conn:
            conn.execute(text(insert_sql), params)

        logger.info("Lineage and governance audit recorded for batch '%s' (%s).", batch_id, dq_status)
