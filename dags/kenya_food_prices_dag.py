from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    try:
        from airflow.providers.standard.operators.python import PythonOperator
        from airflow import DAG
        AIRFLOW_AVAILABLE = True
    except ImportError:
        AIRFLOW_AVAILABLE = False

from src.ingestion import ingest_raw_food_prices
from src.transformation import clean_and_normalize_food_prices
from src.warehouse import get_engine, load_fact_table
from src.data_quality import DataQualityEngine


def ingest_task_callable(**context):
    raw_path, meta = ingest_raw_food_prices()
    ti = context.get("ti")
    if ti:
        ti.xcom_push(key="raw_path", value=str(raw_path))
        ti.xcom_push(key="checksum", value=meta.get("checksum_sha256"))
    return str(raw_path)


def transform_task_callable(**context):
    ti = context.get("ti")
    raw_path = ti.xcom_pull(task_ids="ingest_raw_data", key="raw_path") if ti else None
    cleaned_df = clean_and_normalize_food_prices(raw_path or "data/raw/wfp_food_prices_kenya_raw.csv")
    if ti:
        ti.xcom_push(key="cleaned_rows", value=len(cleaned_df))
    return len(cleaned_df)


def load_task_callable(**context):
    import pandas as pd
    from src.config import settings
    cleaned_csv = settings.processed_data_dir / "kenya_food_prices_cleaned.csv"
    df = pd.read_csv(cleaned_csv)
    engine = get_engine()
    rows = load_fact_table(df, engine=engine, if_exists="append")
    ti = context.get("ti")
    if ti:
        ti.xcom_push(key="fact_rows", value=rows)
    return rows


def quality_check_callable(**context):
    engine = get_engine()
    dq = DataQualityEngine(engine)
    passed, results = dq.run_all_validation_checks()

    ti = context.get("ti")
    batch_id = f"AIRFLOW-BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    raw_count = ti.xcom_pull(task_ids="transform_clean_data", key="cleaned_rows") if ti else 0
    fact_count = ti.xcom_pull(task_ids="load_star_schema", key="fact_rows") if ti else 0

    dq.record_lineage(
        batch_id=batch_id,
        source_uri="https://data.humdata.org/dataset/wfp-food-prices-for-kenya",
        raw_count=raw_count or 0,
        cleaned_count=raw_count or 0,
        fact_count=fact_count or 0,
        duration_sec=12.4,
        dq_results=results,
    )

    if not passed:
        raise ValueError(f"Data quality checks failed: {[r['check_name'] for r in results if not r['passed']]}")
    return "All quality checks passed"


default_args = {
    "owner": "Peter",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

if AIRFLOW_AVAILABLE:
    dag = DAG(
        "kenya_food_prices_monthly_pipeline",
        default_args=default_args,
        description="Automated monthly ETL and validation pipeline for Kenya Food Prices",
        schedule="@monthly",
        catchup=False,
        max_active_runs=1,
    )

    task_ingest = PythonOperator(
        task_id="ingest_raw_data",
        python_callable=ingest_task_callable,
        dag=dag,
    )

    task_transform = PythonOperator(
        task_id="transform_clean_data",
        python_callable=transform_task_callable,
        dag=dag,
    )

    task_load = PythonOperator(
        task_id="load_star_schema",
        python_callable=load_task_callable,
        dag=dag,
    )

    task_quality = PythonOperator(
        task_id="run_data_quality_audit",
        python_callable=quality_check_callable,
        dag=dag,
    )

    task_ingest >> task_transform >> task_load >> task_quality
