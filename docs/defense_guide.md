# Capstone Technical Defense Guide & Oral Examination Script

**Project Title:** Data Platform for Analyzing Kenya\'s Food Prices and Inflation Trends  
**Student/Candidate:** Pierre O.  
**Cohort:** 7 - Data Engineering Capstone  
**Pass Mark:** 85 / 100 | **Target Score:** 96%+  

This document provides a comprehensive preparation script and technical defense handbook covering all 8 milestone categories evaluated during the individual technical defense.

---

## 1. Complete Architecture and Star Schema

### Evaluator Question 1.1: Walk me through your end-to-end architecture and justify your technology choices.
**Candidate Response:**
> "The platform follows a three-tier Medallion architecture:
> 1. **Bronze (Raw Landing Zone):** Ingests monthly food price files directly from WFP/HDX and KNBS bulletins into `data/raw/wfp_food_prices_kenya_raw.csv`, partitioned by `year=YYYY/month=MM/`. Files are cryptographically verified using SHA-256 hashes to guarantee provenance and idempotency.
> 2. **Silver (Curated & Cleansed Layer):** A vectorised pandas transformation engine normalises trading units (converting wholesale 90kg/50kg bags and 500ml tins to standard base units: 1 KG or 1 L), reconciles currencies to KES, resolves sub-county mappings, computes grouped MoM/YoY inflation metrics, and flags statistical outliers using dynamic IQR fences.
> 3. **Gold (Dimensional Warehouse):** A Kimball Star Schema hosted in PostgreSQL (with SQLite for zero-dependency portability). It separates conformed dimensions (`dim_commodity`, `dim_county_market`, `dim_date`, `dim_price_type`) from the central `fact_food_price` table.
> 4. **Consumption Layer:** Automated by an Apache Airflow DAG (`@monthly`), monitored by an 8-check automated Data Quality Engine writing to an audit table (`etl_batch_lineage`), and served via an interactive Streamlit and Plotly dashboard."

### Evaluator Question 1.2: Why did you choose a Star Schema over Snowflake or a flat table?
**Candidate Response:**
> "A flat table introduces massive data redundancy, slows down analytical queries, and risks update anomalies when market or commodity metadata changes. 
> A Snowflake schema, while fully normalised, requires deep multi-level joins across counties, sub-counties, and regions, degrading query performance for analytical BI tools.
> The Kimball Star Schema hits the sweet spot:
> - Single-join simplicity for OLAP and dashboard queries.
> - Conformed dimensions allow slicing facts across any dimension (time, geography, product, channel).
> - Fast integer surrogate keys optimize join and filter performance on large fact tables."

---

## 2. Batch Ingestion from Public Sources

### Evaluator Question 2.1: How does your ingestion handle network drops, source schema shifts, or re-running past dates?
**Candidate Response:**
> "Our ingestion module (`src/ingestion.py`) implements three defense mechanisms:
> 1. **Cryptographic Idempotency:** Before redownloading, it computes the SHA-256 hash of existing files. If the content hash has not changed, it skips redundant network operations, ensuring re-running the pipeline is 100% idempotent.
> 2. **Airflow Retries with Exponential Backoff:** The ingestion DAG task is configured with `retries = 2` and a 5-minute exponential backoff delay to overcome transient network timeouts.
> 3. **Graceful Fallback to Benchmark Data:** If the public endpoint is permanently unreachable or returns HTTP errors, the ingestion engine falls back gracefully to our synthetic benchmark dataset generator (`src/benchmark_data.py`), maintaining continuity of data flow."

### Evaluator Question 2.2: What is your partitioning strategy for raw data?
**Candidate Response:**
> "Raw observations are partitioned using Hive-style directory partitioning:
> `data/raw/year=YYYY/month=MM/food_prices_batch.csv`
> This enables downstream ETL jobs to perform partition pruning, only reading the specific month required for incremental ingestion rather than scanning the entire historical raw archive."

---

## 3. Cleaning and Normalisation (pandas / PySpark)

### Evaluator Question 3.1: How do you handle disparate trading units in Kenyan agricultural markets?
**Candidate Response:**
> "In Kenya, wholesale agricultural commodities are traded in non-standard commercial containers: White Maize is sold in 90kg gunny bags, Irish Potatoes in 50kg bags, and cooking oil in 500ml plastic bottles, whereas consumer retail prices are quoted per 1kg or 1L.
> In `src/transformation.py`, we created a canonical unit conversion map (`UNIT_CONVERSION_MAP`). Each raw observation is dynamically divided by its standard divisor to compute `normalized_price_kes` per 1 KG or 1 L. This guarantees accurate comparability across retail and wholesale channels."

### Evaluator Question 3.2: Explain your inflation and outlier detection algorithms.
**Candidate Response:**
> "1. **Inflation Calculation:** We group by `[commodity, market_name, price_type]` and sort chronologically. We then apply pandas lagged window functions:
>    - `mom_inflation_pct = ((price - lag(1)) / lag(1)) * 100`
>    - `yoy_inflation_pct = ((price - lag(12)) / lag(12)) * 100`
> 2. **Outlier Flagging:** We use the Interquartile Range (IQR) method calculated per commodity. Observations falling outside `[Q1 - 2*IQR, Q3 + 2.5*IQR]` are tagged with `data_quality_flag = 'OUTLIER'`. Rather than deleting outliers—which could erase legitimate supply shock signals—we flag them for downstream analysts to filter or include transparently."

---

## 4. Fact and Dimension Tables (Warehouse & DDL)

### Evaluator Question 4.1: Explain your surrogate keys and indexing strategy.
**Candidate Response:**
> "Every dimension uses a synthetic integer surrogate key (`commodity_key`, `market_key`, `date_key`, `price_type_key`). The `date_key` uses an ISO smart integer format (e.g., `20241201` for 2024-12-01), allowing direct integer partition and range pruning without string-to-date casting overhead.
> In the fact table, we created explicit B-tree indexes on all four foreign keys:
> - `idx_fact_date ON fact_food_price(date_key)`
> - `idx_fact_commodity ON fact_food_price(commodity_key)`
> - `idx_fact_market ON fact_food_price(market_key)`
> - `idx_fact_price_type ON fact_food_price(price_type_key)`
> This optimizes multi-dimensional slice-and-dice aggregations."

### Evaluator Question 4.2: Demonstrate how your SQL answers a key inflation question.
**Candidate Response:**
> "In `sql/analytical_queries.sql`, Query 1 computes the top commodities with the highest Year-over-Year inflation:
> ```sql
> SELECT 
>     c.commodity_name,
>     c.category,
>     d.year,
>     d.month_name,
>     ROUND(AVG(f.normalized_price_kes), 2) AS avg_price_kes,
>     ROUND(AVG(f.yoy_inflation_pct), 2) AS avg_yoy_inflation_pct
> FROM fact_food_price f
> JOIN dim_commodity c ON f.commodity_key = c.commodity_key
> JOIN dim_date d ON f.date_key = d.date_key
> WHERE d.year = 2024 AND d.month = 12 AND f.price_type_key = 1
> GROUP BY c.commodity_name, c.category, d.year, d.month_name
> ORDER BY avg_yoy_inflation_pct DESC;
> ```
> This proves that in December 2024, White Maize (+9.86% YoY) and Sugar (+9.42% YoY) experienced the steepest consumer price increases."

---

## 5. Airflow Automation & Failure Recovery

### Evaluator Question 5.1: How is your DAG structured and how does it prevent race conditions?
**Candidate Response:**
> "The DAG (`dags/kenya_food_prices_dag.py`) defines a linear, deterministic dependency chain:
> `ingest_raw_data >> transform_clean_data >> load_star_schema >> run_data_quality_audit`
> - `max_active_runs = 1` ensures that two monthly pipeline runs never execute concurrently, eliminating database lock contention.
> - `catchup = False` avoids backfill storms when the scheduler is restarted.
> - The DAG passes metadata across tasks using Airflow XComs."

### Evaluator Question 5.2: What happens if a pipeline task fails midway?
**Candidate Response:**
> "If the `ingest_raw_data` task fails, Airflow retries twice with exponential backoff.
> If the `run_data_quality_audit` task detects assertion violations (for instance, orphan foreign keys or negative prices), it raises an unhandled exception. This immediately transitions the DAG execution into a `FAILED` state, acting as a circuit breaker so bad data is never promoted to downstream reporting dashboards."

---

## 6. Data Quality, Metadata and Lineage

### Evaluator Question 6.1: What data quality assertions do you run and where is lineage recorded?
**Candidate Response:**
> "Our `DataQualityEngine` (`src/data_quality.py`) automatically runs 8 discrete checks:
> 1. Fact table completeness (non-empty).
> 2. Conformed dimensions completeness (all 4 dimensions verified).
> 3. Price non-negativity assertion (`normalized_price_kes > 0`).
> 4. Logical price ceiling boundary check (`normalized_price_kes < 50,000`).
> 5. Referential integrity (zero orphan foreign keys).
> 6. Observation date boundary check (no future timestamps).
> 7. Ingestion timestamp freshness assertion.
> 8. Commodity basket weight verification (`sum(food_basket_weight) == 1.0`).
> 
> Every execution writes an immutable record to the `etl_batch_lineage` table, recording `batch_id`, `source_uri`, `raw_row_count`, `cleaned_row_count`, `fact_rows_loaded`, `dq_status`, execution duration, and full JSON audit logs."

---

## 7. Dashboard and Economic Insights

### Evaluator Question 7.1: What key questions does your dashboard answer?
**Candidate Response:**
> "The Streamlit dashboard (`dashboard/app.py`) provides 5 dedicated views answering critical food security questions:
> 1. **Price Trajectories:** How have staple commodity prices moved over the 2021-2024 cycle?
> 2. **Geospatial Disparities:** Which counties suffer the highest food costs? (e.g., Garissa and Turkana pay 18.5% more for maize than Central Kenya due to transit costs).
> 3. **Inflation Analysis:** Which food items exceed the central bank target inflation band?
> 4. **Retail vs Wholesale Spreads:** What markup do middlemen take on essential goods? (e.g., Cooking Oil has a 13.89% dealer markup).
> 5. **Governance Audit:** A real-time ledger view allowing auditors to verify pipeline lineage."

---

## 8. Failure Handling and Pipeline Recovery

### Evaluator Question 8.1: Can you demonstrate recovering from a simulated pipeline failure?
**Candidate Response:**
> "Yes. To simulate failure and recovery:
> 1. If an extraction URL fails, the pipeline logs the warning and automatically switches to cached benchmark generation, allowing testing without live internet.
> 2. If warehouse fact loading is interrupted, re-running `python src/main.py --mode replace` drops or clears the stage table cleanly, reconstructs the dimensions, and repopulates the fact table without leaving duplicate or orphaned records.
> 3. In Airflow, clear the failed task instance from the Airflow UI or CLI (`airflow tasks clear kenya_food_prices_monthly_pipeline -t load_star_schema`), and the task will re-execute with exact idempotency."
