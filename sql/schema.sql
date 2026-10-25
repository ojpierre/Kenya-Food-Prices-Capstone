-- DDL for Kenya Food Prices Star Schema Data Warehouse
-- Supported dialects: PostgreSQL, SQLite

CREATE TABLE IF NOT EXISTS dim_commodity (
    commodity_key INTEGER PRIMARY KEY,
    commodity_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    standard_unit VARCHAR(20) NOT NULL,
    food_basket_weight DECIMAL(4, 2) NOT NULL DEFAULT 0.10
);

CREATE TABLE IF NOT EXISTS dim_county_market (
    market_key INTEGER PRIMARY KEY,
    market_name VARCHAR(100) NOT NULL UNIQUE,
    sub_county VARCHAR(100) NOT NULL,
    county_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, -- Format YYYYMMDD
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    is_harvest_season BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS dim_price_type (
    price_type_key INTEGER PRIMARY KEY,
    price_type_name VARCHAR(20) NOT NULL UNIQUE,
    channel_description VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS fact_food_price (
    price_id INTEGER PRIMARY KEY,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    commodity_key INTEGER NOT NULL REFERENCES dim_commodity(commodity_key),
    market_key INTEGER NOT NULL REFERENCES dim_county_market(market_key),
    price_type_key INTEGER NOT NULL REFERENCES dim_price_type(price_type_key),
    raw_price DECIMAL(10, 2) NOT NULL,
    raw_unit VARCHAR(50) NOT NULL,
    normalized_price_kes DECIMAL(10, 2) NOT NULL,
    normalized_unit VARCHAR(20) NOT NULL,
    mom_inflation_pct DECIMAL(6, 2),
    yoy_inflation_pct DECIMAL(6, 2),
    data_quality_flag VARCHAR(20) NOT NULL DEFAULT 'VALID',
    ingested_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_food_price(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_commodity ON fact_food_price(commodity_key);
CREATE INDEX IF NOT EXISTS idx_fact_market ON fact_food_price(market_key);
CREATE INDEX IF NOT EXISTS idx_fact_price_type ON fact_food_price(price_type_key);
