# Milestone 1: Platform Architecture

## End-to-End Platform Design

`
+-----------------------------------------------------------------------------------------+
|                                DATA INGESTION & LANDING                                 |
|  - WFP / HDX Kenya Food Prices Public Endpoint                                          |
|  - Idempotent Python Ingestion Engine (src/ingestion.py)                                 |
|  - Landing Zone: Partitioned Raw Storage (data/raw/year=YYYY/month=MM/)                 |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                            CLEANING & NORMALISATION LAYER                               |
|  - Data Cleansing & Validation Engine (src/transformation.py)                            |
|  - Standardized KES per KG / KES per Liter Unit Converter                               |
|  - Commodity, Market, and Date Conforming                                               |
|  - Processed Staging Storage (data/processed/kenya_food_prices_clean.parquet / .csv)    |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                           ANALYTICAL STAR SCHEMA WAREHOUSE                              |
|  - SQLAlchemy 2.0 Warehouse Loader (src/warehouse.py)                                   |
|  - Relational Storage: PostgreSQL (Production) / SQLite / DuckDB (Dev & CI)             |
|  - Dimensions: dim_commodity, dim_county_market, dim_date, dim_price_type               |
|  - Central Fact: fact_food_price (with MoM and YoY Inflation Metrics)                    |
+---------------------+---------------------------------------------+---------------------+
                      |                                             |
                      v                                             v
+-------------------------------------------+ +-------------------------------------------+
|       DATA QUALITY & GOVERNANCE           | |         ORCHESTRATION & AUTOMATION        |
|  - Automated Assertions (src/quality.py)  | |  - Airflow DAG (dags/food_prices_dag.py)  |
|  - Schema, Null, Range, & FK Integrity    | |  - Dependency Graph & Automated Retries   |
|  - Audit Ledger: etl_batch_lineage table  | |  - Error Alerts & Recovery Strategy       |
+---------------------+---------------------+ +---------------------+---------------------+
                      |                                             |
                      +----------------------+----------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                            PRESENTATION & VISUALIZATION                                 |
|  - Interactive Streamlit Dashboard (dashboard/app.py)                                   |
|  - Historical Commodity Price Trends & Regional Inflation Heatmaps                      |
|  - Retail vs Wholesale Margin Analytics                                                 |
|  - Pre-built Analytical SQL Queries (sql/analytical_queries.sql)                        |
+-----------------------------------------------------------------------------------------+
`

---

## Component Descriptions

1. **Ingestion Layer**:
   - Re-runnable, idempotent Python batch extractor.
   - Downloads source snapshots from the public HDX/KNBS repository, checks MD5/SHA256 file hashes to prevent redundant downloads, and partitions raw files into data/raw/.

2. **Transformation Layer**:
   - Implemented in Python with pandas.
   - Handles missing value imputation, unit conversion to uniform base measurements (per KG, per Liter), outlier flagging, and monthly/yearly inflation calculations.

3. **Warehouse Layer**:
   - Star schema architecture implemented in PostgreSQL (with SQLite zero-dependency fallback for local grading).
   - Separates conformed dimensions from quantitative price transactions to enable high-performance analytical queries.

4. **Quality & Governance Layer**:
   - Automated quality test suite asserting non-null constraints, price boundary sanity (e.g. price > 0 and price < 50,000 KES), and referential integrity between fact and dimension foreign keys.
   - Lineage ledger recording each run's execution timestamp, row counts, hash checksums, and pass/fail statuses.

5. **Presentation Layer**:
   - Streamlit dashboard and analytical SQL scripts answering core macroeconomic and policy questions regarding food security and regional inflation in Kenya.
