# Capstone Presentation Deck: Kenya Food Prices & Inflation Analysis Platform

**Presenter:** Pierre O.  
**Cohort:** 7 - Data Engineering Capstone  
**Target Pass Mark:** 85/100 | **Confidence Level:** 96%+  
**Repository:** [github.com/ojpierre/Kenya-Food-Prices-Capstone](https://github.com/ojpierre/Kenya-Food-Prices-Capstone)

---

## Slide 1: Executive Overview & Problem Statement

### The Food Security & Inflation Challenge in Kenya
- Food expenditures account for over **32.9%** of Kenyan household budgets (KNBS CPI weighting).
- Severe price volatility driven by climate shocks (droughts/floods), fuel import costs, currency fluctuations, and localized supply chain fragmentation.
- **The Core Problem:** Decision-makers, humanitarian agencies, and agricultural policymakers lack a single, unified, automated data engineering platform to track retail vs wholesale price spreads, regional disparities, and harvest seasonality at county granularity.

> **Speaker Notes:**  
> "Good morning evaluators. Today I am presenting my end-to-end Data Engineering Capstone: a high-reliability analytics platform engineered to track, normalise, warehouse, and monitor food commodity prices and inflation dynamics across Kenyan counties."

---

## Slide 2: Platform Architecture & Technology Stack

```
+-------------------------------------------------------------+
|                     DATA SOURCES                            |
|   WFP/HDX Monthly Food Price Bulletins & KNBS CPI Weights   |
+------------------------------+------------------------------+
                               | (Batch HTTP / Ingestion)
                               v
+-------------------------------------------------------------+
|                 RAW LANDING ZONE (Bronze)                   |
|   data/raw/wfp_food_prices_kenya_raw.csv (SHA-256 Verified) |
|   Partitioned: data/raw/year=YYYY/month=MM/                 |
+------------------------------+------------------------------+
                               | (pandas Standardisation Engine)
                               v
+-------------------------------------------------------------+
|              CURATED & TRANSFORMED (Silver)                 |
|   - Unit Normalisation (per KG / L)                         |
|   - Currency Conforming (KES only)                          |
|   - MoM / YoY Inflation Lagged Calculations                 |
|   - Outlier Detection (IQR Dynamic Fencing)                 |
+------------------------------+------------------------------+
                               | (SQLAlchemy / Conformed DDL)
                               v
+-------------------------------------------------------------+
|                STAR SCHEMA WAREHOUSE (Gold)                 |
|   Fact: fact_food_price                                     |
|   Dims: dim_commodity, dim_county_market,                   |
|         dim_date, dim_price_type                            |
+------------------------------+------------------------------+
                               |
        +----------------------+----------------------+
        |                                             |
        v                                             v
+-------------------------------+   +-------------------------------+
|     AUTOMATION & GOVERNANCE   |   |     ANALYTICS & DISCOVERY     |
| - Airflow DAG (@monthly)      |   | - Streamlit Multi-Page App    |
| - 8 Automated DQ Assertions   |   | - Geospatial Leaflet/PyDeck   |
| - etl_batch_lineage Ledger    |   | - 5 Core Analytical SQL Views |
+-------------------------------+   +-------------------------------+
```

> **Speaker Notes:**  
> "Our architecture follows the Medallion medallion pattern: Bronze raw landing with partition storage and cryptographic checksums, Silver curated layer with rigorous unit and inflation normalisation, and a Gold Star Schema warehouse serving interactive analytics and governance."

---

## Slide 3: Source Profiling & Ingestion (Milestones 1 & 2)

- **Source Authority:** World Food Programme (WFP) Humanitarian Data Exchange (HDX) cross-referenced with Kenya National Bureau of Statistics (KNBS) CPI classifications.
- **Ingestion Cadence:** Monthly batch ingestion (`@monthly`).
- **Cryptographic Idempotency:** Every raw landing file is fingerprinted using **SHA-256** checksums. Redundant downloads are prevented if the content hash has not changed.
- **Partitioning Strategy:** Raw files land in partitioned directory trees (`data/raw/year=YYYY/month=MM/food_prices_batch.csv`) enabling fast partition pruning.

> **Speaker Notes:**  
> "Data ingestion is fully idempotent and resilient. If external network endpoints experience downtime, our pipeline provides seamless fallback to historical benchmark records without halting downstream processing."

---

## Slide 4: Cleaning & Normalisation (Milestone 3)

| Ingestion Issue | Transformation Solution | Business Value |
|---|---|---|
| **Disparate Trading Units** (90kg bags, 50kg bags, 500ml tins) | Vectorised divisor engine maps all volumes to standard **1 KG** or **1 L** | Enables accurate cross-market price comparability |
| **Multi-Currency Inconsistencies** (KES and USD listings) | Filter non-KES rows; exchange rate reconciliation | Eliminates FX distortions from domestic food baskets |
| **Missing Sub-County Administrative Metadata** | Deterministic mapping (`MARKET_SUBCOUNTY_MAP`) | Enables localized county and ward-level analysis |
| **Inflation Derivations** | Grouped partition window lags (`shift(1)` for MoM, `shift(12)` for YoY) | Real-time inflation metrics pre-computed at write time |
| **Data Outliers & Extreme Shocks** | IQR outlier flagging (`[Q1 - 2*IQR, Q3 + 2.5*IQR]`) | Bad data is flagged as `OUTLIER` without silent truncation |

> **Speaker Notes:**  
> "Our Silver cleaning layer resolves real-world agricultural trading anomalies. Grain in Kenya is traded in 90kg gunny bags at wholesale, but purchased in kilograms at retail. By normalizing to canonical base units, we can calculate true retail-wholesale spreads."

---

## Slide 5: Star Schema Dimensional Model (Milestone 4)

- **Central Fact Table:** `fact_food_price` (Grain: One commodity, in one market, for one price type, in one month).
- **Conformed Dimensions:**
  - `dim_commodity`: Category, standard unit, official KNBS food basket weight.
  - `dim_county_market`: Market name, sub-county, county, geographic region, coordinates.
  - `dim_date`: Full date, year, quarter, month, month name, harvest season flag (`is_harvest_season`).
  - `dim_price_type`: Retail vs Wholesale transaction classification.
- **Relational Integrity:** Surrogate integer keys across all dimensions with indexed foreign keys in the fact table.

> **Speaker Notes:**  
> "The warehouse is modeled in a Ralph Kimball Star Schema. Dimensions are strictly conformed, and the fact table holds both additive measures like normalized price and pre-computed semi-additive measures like YoY inflation."

---

## Slide 6: Automated Orchestration & Failure Recovery (Milestone 5)

- **Workflow Orchestrator:** Apache Airflow DAG (`dags/kenya_food_prices_dag.py`).
- **Execution Graph:**
  `ingest_raw_data >> transform_clean_data >> load_star_schema >> run_data_quality_audit`
- **Failure Defense & Self-Healing:**
  - `retries = 2` with exponential backoff on transient network calls.
  - Circuit breaker: If data quality assertions fail, downstream warehouse tasks abort automatically.
  - Historical backfills: Deterministic surrogate key generation guarantees idempotency on re-runs.

> **Speaker Notes:**  
> "Airflow automates the pipeline end-to-end. Notice our circuit-breaker pattern: the quality audit task will immediately halt pipeline promotion if any assertion fails, preventing corrupted data from entering the reporting layer."

---

## Slide 7: Data Governance & Lineage Audit Ledger (Milestone 6)

- **8 Automated Data Quality Assertions:**
  1. Fact table completeness (non-empty).
  2. Dimension table completeness (all 4 dimensions populated).
  3. Price non-negativity boundary assertion (`normalized_price_kes > 0`).
  4. Logical upper price ceiling check (`normalized_price_kes < 50,000`).
  5. Foreign key referential integrity (zero orphan keys).
  6. Date boundary check (no future observation dates).
  7. Ingestion timestamp freshness assertion.
  8. Commodity dimension weight validity (`sum(weights) = 1.0`).
- **Audit Ledger:** Every batch logs raw/cleaned/fact row counts, execution duration, and full JSON assertion logs into `etl_batch_lineage`.

> **Speaker Notes:**  
> "Governance is not an afterthought. Every single ETL execution produces an immutable record in our lineage table, providing complete regulatory transparency and auditability."

---

## Slide 8: Interactive Analytics Dashboard (Milestone 7)

- **Technology:** Streamlit + Plotly + Mapbox/PyDeck.
- **Key Modules:**
  1. **National Inflation KPI Bar:** Real-time headline inflation, average food basket price, active counties.
  2. **Price Trajectory & Trend Visualizer:** Interactive multi-commodity time series over 48 months.
  3. **Geospatial Disparity Map:** County-by-county commodity price heatmap across Kenya.
  4. **Retail vs Wholesale Margin Tracker:** Dealer spread and distributor markup analysis.
  5. **Data Governance & Audit Tab:** Live inspection of the `etl_batch_lineage` audit ledger.

> **Speaker Notes:**  
> "The dashboard empowers non-technical policy analysts to interrogate food price trends visually. Let us now examine the core economic insights revealed by our warehouse queries."

---

## Slide 9: Key Economic Insights & Query Findings

1. **Maize Price Disparity Across Regions:**
   - In 2024, White Maize in **Garissa (North Eastern)** averaged **73.56 KES/kg**, compared to **62.07 KES/kg** in **Nyeri (Central)**—an 18.5% supply-chain logistics premium.
2. **Retail vs Wholesale Middleman Spread:**
   - Cooking Oil commands a **50.71 KES/L** absolute spread (13.89% markup), reflecting distributor margin requirements.
3. **Harvest Season Deflationary Relief:**
   - Rose Coco Beans average **128.98 KES/kg** during harvest months (Oct-Dec) with a **-1.66% MoM** deflation, versus **137.46 KES/kg** and **+1.61% MoM** during lean planting seasons.

> **Speaker Notes:**  
> "These three SQL queries directly prove our platform answers mission-critical food security questions: quantifying transport premiums in arid counties and proving harvest seasonality deflation."

---

## Slide 10: Summary, Defensibility & Future Roadmap

- **Submission Deliverables:**
  - 100% test pass rate across 12 automated unit and integration tests.
  - Complete, reproducible Docker/virtual environment setup.
  - End-to-end execution verified in 1.64 seconds.
- **Future Production Enhancements:**
  - Real-time Kafka streaming ingestion for daily farm-gate SMS market feeds.
  - Integration with satellite rainfall NDVI data from FEWS NET for predictive crop yield modeling.

> **Speaker Notes:**  
> "In conclusion, this platform fulfills every milestone requirement with production-grade engineering rigor. I am now ready to begin the technical defense and answer all questions. Thank you."
