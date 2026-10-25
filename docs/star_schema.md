# Milestone 1: Star Schema Warehouse Design

## 1. Dimensional Model Overview

The warehouse follows Kimball dimensional modeling principles designed for fast slicing, dicing, and time-series aggregation of food inflation metrics.

`mermaid
erDiagram
    dim_commodity ||--o{ fact_food_price : "categorizes"
    dim_county_market ||--o{ fact_food_price : "located_at"
    dim_date ||--o{ fact_food_price : "observed_on"
    dim_price_type ||--o{ fact_food_price : "sold_via"

    dim_commodity {
        int commodity_key PK
        string commodity_name
        string category
        string standard_unit
        float food_basket_weight
    }

    dim_county_market {
        int market_key PK
        string market_name
        string sub_county
        string county_name
        string region
        float latitude
        float longitude
    }

    dim_date {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        string month_name
        boolean is_harvest_season
    }

    dim_price_type {
        int price_type_key PK
        string price_type_name
        string channel_description
    }

    fact_food_price {
        bigint price_id PK
        int date_key FK
        int commodity_key FK
        int market_key FK
        int price_type_key FK
        float raw_price
        string raw_unit
        float normalized_price_kes
        string normalized_unit
        float mom_inflation_pct
        float yoy_inflation_pct
        string data_quality_flag
        timestamp ingested_at
    }
`

---

## 2. Table Specifications

### Fact Table: act_food_price
- **Granularity**: One record per commodity, per market, per transaction channel (Retail/Wholesale), per observation period (month).
- **Business Measures**:
  - aw_price: The original price reported in the source file.
  - 
ormalized_price_kes: Calculated unit price in KES per canonical unit (1 KG or 1 Liter).
  - mom_inflation_pct: Month-over-Month percentage price change for the same commodity in the same market.
  - yoy_inflation_pct: Year-over-Year percentage price change for the same commodity in the same market.

### Dimension Table: dim_commodity
- Stores master commodity attributes, grouping food items into official categories (*Cereals & Tubers*, *Pulses & Nuts*, *Vegetables & Fruits*, *Oils & Fats*, *Milk & Dairy*, *Meat & Fish*).

### Dimension Table: dim_county_market
- Stores geospatial and administrative market hierarchy (*Market* -> *Sub-County* -> *County* -> *Region*).
- Regions conform to Kenya's 8 traditional economic regions: *Central*, *Coast*, *Eastern*, *Nairobi*, *North Eastern*, *Nyanza*, *Rift Valley*, *Western*.

### Dimension Table: dim_date
- Conformed calendar dimension with attributes for year, quarter, month, and agricultural seasonality flag (is_harvest_season).

### Dimension Table: dim_price_type
- Differentiates between *Retail* (consumer facing) and *Wholesale* (bulk trader) transactions.
