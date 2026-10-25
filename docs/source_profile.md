# Milestone 1: Source Profiling Document

## 1. Overview and Selected Source

For this capstone data platform, the primary source selected is the **World Food Programme (WFP) Humanitarian Data Exchange (HDX) Kenya Food Prices Dataset**, benchmarked against the **Kenya National Bureau of Statistics (KNBS) Consumer Price Index (CPI) Food Basket**.

- **Source Name**: WFP / UN OCHA Humanitarian Data Exchange - Kenya Food Prices Monitoring
- **Publisher**: UN World Food Programme Vulnerability Analysis and Mapping (WFP-VAM)
- **Official Portal**: [HDX Kenya Food Prices](https://data.humdata.org/dataset/wfp-food-prices-for-kenya)
- **Dataset File**: wfp_food_prices_ken.csv
- **Geographic Coverage**: Kenya (National, 47 Counties, 50+ Primary Urban and Rural Markets)
- **Temporal Coverage**: January 2006 – Present
- **Update Cadence**: Monthly batch updates
- **Licensing and Terms of Use**: Creative Commons Attribution for Intergovernmental Organisations (CC-BY-IGO 3.0). Free for public, educational, and commercial analytical usage with mandatory attribution.

---

## 2. Source Schema and Data Types

The raw dataset contains observation records structured as follows:

| Field Name | Raw Type | Description | Sample Value | Expected Nulls |
|------------|----------|-------------|--------------|----------------|
| date | String | Observation period (YYYY-MM-DD or YYYY-MM) | 2024-01-15 | 0% |
| dmin1 | String | County / Provincial administration unit | Nairobi | < 1% |
| dmin2 | String | Sub-County / District administration unit | Starehe | ~ 5% |
| market | String | Monitoring market / trading station | Gikomba | 0% |
| latitude | Float | Geospatial latitude coordinate | -1.286389 | ~ 2% |
| longitude | Float | Geospatial longitude coordinate | 36.837222 | ~ 2% |
| category | String | Food basket category | cereals and tubers | 0% |
| commodity| String | Specific food commodity name | Maize (white) | 0% |
| unit | String | Transaction unit of measure | 90 KG, KG, L | 0% |
| priceflag | String | Data collection flag (actual, aggregate, forecast) | ctual | 0% |
| pricetype | String | Trading channel (Retail, Wholesale) | Retail | 0% |
| currency | String | Local transaction currency code | KES | 0% |
| price | Float | Recorded local price in KES | 4500.0 | < 0.5% |
| usdprice | Float | Converted price in USD | 31.25 | < 0.5% |

---

## 3. Data Profiling Findings and Quality Risks

1. **Packaging Unit Inconsistencies**:
   - Grains and pulses are recorded in heterogeneous packaging units: 90 KG bag, 50 KG bag, 100 KG bag, and 1 KG.
   - Liquid items (cooking oil, milk) appear as Liter, 500 ML, or Jerrycan (20L).
   - *Mitigation*: The normalization layer standardizes all commodities to canonical base units (KES per KG or KES per Liter).

2. **Market Naming Variations and Missing Sub-Counties**:
   - dmin2 (sub-county) has ~5% missing values, and market names occasionally feature alternate transliterations (e.g., Lodwar Town vs Lodwar).
   - *Mitigation*: Conformed county-market dimension mapping with default imputation for missing administrative sub-units based on market latitude/longitude.

3. **Macroeconomic and Seasonal Outliers**:
   - Kenyan food prices exhibit sharp seasonal fluctuations during drought periods and post-harvest months (October-December).
   - *Mitigation*: Outlier boundary checks using interquartile range (IQR) to flag anomalies without prematurely deleting valid economic crisis data points.

4. **Temporal Alignment**:
   - Some historical records use monthly snapshots (2023-05-15) while others use first-of-month (2023-05-01).
   - *Mitigation*: Normalize all dates to standard first-of-month dates (YYYY-MM-01) linked to the dimensional calendar table.
