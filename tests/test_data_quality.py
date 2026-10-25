import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.data_quality import DataQualityEngine
from src.transformation import clean_and_normalize_food_prices
from src.warehouse import load_fact_table


def test_data_quality_suite_passes(sample_raw_df: pd.DataFrame, sqlite_test_engine: Engine):
    cleaned = clean_and_normalize_food_prices(sample_raw_df)
    load_fact_table(cleaned, sqlite_test_engine, if_exists="replace")

    dq_engine = DataQualityEngine(sqlite_test_engine)
    all_passed, results = dq_engine.run_all_validation_checks()

    assert all_passed is True
    assert len(results) == 8
    for r in results:
        assert r["passed"] is True


def test_lineage_recording(sample_raw_df: pd.DataFrame, sqlite_test_engine: Engine):
    cleaned = clean_and_normalize_food_prices(sample_raw_df)
    fact_count = load_fact_table(cleaned, sqlite_test_engine, if_exists="replace")

    dq_engine = DataQualityEngine(sqlite_test_engine)
    all_passed, results = dq_engine.run_all_validation_checks()

    dq_engine.record_lineage(
        batch_id="TEST-BATCH-001",
        source_uri="https://test.data/sample.csv",
        raw_count=len(sample_raw_df),
        cleaned_count=len(cleaned),
        fact_count=fact_count,
        duration_sec=0.45,
        dq_results=results,
    )

    with sqlite_test_engine.connect() as conn:
        lineage_row = conn.execute(text("SELECT * FROM etl_batch_lineage WHERE batch_id = 'TEST-BATCH-001'")).fetchone()
        assert lineage_row is not None
        assert lineage_row[0] == "TEST-BATCH-001"
        assert lineage_row[1] == "https://test.data/sample.csv"
        assert lineage_row[9] == "PASSED"
