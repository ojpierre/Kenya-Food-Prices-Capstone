# Milestone 5: Airflow Automation and Failure Recovery

## 1. DAG Architecture

The automated monthly pipeline is orchestrated by dags/kenya_food_prices_dag.py:

`
[ingest_raw_data] -> [transform_clean_data] -> [load_star_schema] -> [run_data_quality_audit]
`

- **DAG ID**: kenya_food_prices_monthly_pipeline
- **Schedule**: @monthly
- **Start Date**: 2024-01-01
- **Catchup**: False
- **Concurrency**: max_active_runs = 1

---

## 2. Failure Recovery & Retry Strategy

1. **Transient Network Failures During Extraction**:
   - Source API/network drops are defended with etries = 2 and a 5-minute exponential backoff delay.
   - If public endpoint is down permanently, the ingestion engine falls back gracefully to cached baseline snapshots.

2. **Data Quality Circuit Breaker**:
   - un_data_quality_audit acts as an automated circuit breaker. If critical assertions fail (e.g., negative prices or broken foreign key relationships), the pipeline raises an unhandled exception to fail the DAG run and prevent bad data propagation to analytics tables.

3. **Idempotency & Re-runnability**:
   - Fact table ingestion and dimensional conforming use deterministic surrogate keys and deduplication to ensure re-running a failed or historical batch produces exact, duplicate-free results.
