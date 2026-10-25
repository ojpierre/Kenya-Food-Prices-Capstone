import logging
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

COMMODITY_WEIGHTS = {
    "Maize (white)": 0.25,
    "Beans (rose coco)": 0.15,
    "Potatoes (Irish)": 0.10,
    "Rice (imported)": 0.12,
    "Cooking Oil": 0.10,
    "Cow Milk (fresh)": 0.08,
    "Bread (white)": 0.06,
    "Sugar": 0.08,
    "Sorghum": 0.03,
    "Cabbage": 0.03,
}

COUNTY_REGION_MAP = {
    "Nairobi": "Nairobi",
    "Mombasa": "Coast",
    "Kisumu": "Nyanza",
    "Nakuru": "Rift Valley",
    "Uasin Gishu": "Rift Valley",
    "Nyeri": "Central",
    "Garissa": "North Eastern",
    "Turkana": "Rift Valley",
    "Marsabit": "Eastern",
    "Machakos": "Eastern",
}


def get_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or settings.get_database_url()
    return create_engine(url, pool_pre_ping=True)


def init_warehouse(engine: Engine) -> None:
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS dim_commodity (
            commodity_key INTEGER PRIMARY KEY,
            commodity_name VARCHAR(100) NOT NULL UNIQUE,
            category VARCHAR(50) NOT NULL,
            standard_unit VARCHAR(20) NOT NULL,
            food_basket_weight DECIMAL(4, 2) NOT NULL DEFAULT 0.10
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_county_market (
            market_key INTEGER PRIMARY KEY,
            market_name VARCHAR(100) NOT NULL UNIQUE,
            sub_county VARCHAR(100) NOT NULL,
            county_name VARCHAR(100) NOT NULL,
            region VARCHAR(50) NOT NULL,
            latitude DECIMAL(9, 6),
            longitude DECIMAL(9, 6)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_date (
            date_key INTEGER PRIMARY KEY,
            full_date DATE NOT NULL UNIQUE,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            month INTEGER NOT NULL,
            month_name VARCHAR(20) NOT NULL,
            is_harvest_season BOOLEAN NOT NULL DEFAULT FALSE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_price_type (
            price_type_key INTEGER PRIMARY KEY,
            price_type_name VARCHAR(20) NOT NULL UNIQUE,
            channel_description VARCHAR(100)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_food_price (
            price_id INTEGER PRIMARY KEY,
            date_key INTEGER NOT NULL,
            commodity_key INTEGER NOT NULL,
            market_key INTEGER NOT NULL,
            price_type_key INTEGER NOT NULL,
            raw_price DECIMAL(10, 2) NOT NULL,
            raw_unit VARCHAR(50) NOT NULL,
            normalized_price_kes DECIMAL(10, 2) NOT NULL,
            normalized_unit VARCHAR(20) NOT NULL,
            mom_inflation_pct DECIMAL(6, 2),
            yoy_inflation_pct DECIMAL(6, 2),
            data_quality_flag VARCHAR(20) NOT NULL DEFAULT 'VALID',
            ingested_at TIMESTAMP NOT NULL
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_food_price(date_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_commodity ON fact_food_price(commodity_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_market ON fact_food_price(market_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_price_type ON fact_food_price(price_type_key);",
    ]

    with engine.begin() as conn:
        for stmt in ddl_statements:
            conn.execute(text(stmt))
    logger.info("Star schema tables verified and ready in warehouse.")


def populate_dimensions(df: pd.DataFrame, engine: Engine) -> None:
    # 1. dim_price_type
    price_types = pd.DataFrame([
        {"price_type_key": 1, "price_type_name": "Retail", "channel_description": "Consumer market end-point transactions"},
        {"price_type_key": 2, "price_type_name": "Wholesale", "channel_description": "Bulk trading and distributor transactions"},
    ])
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_price_type;"))
        price_types.to_sql("dim_price_type", con=conn, if_exists="append", index=False)

    # 2. dim_commodity
    comm_df = df[["commodity", "category", "normalized_unit"]].drop_duplicates().copy()
    comm_df = comm_df.rename(columns={"commodity": "commodity_name", "normalized_unit": "standard_unit"})
    comm_df = comm_df.sort_values(by="commodity_name")
    comm_df["commodity_key"] = range(1, len(comm_df) + 1)
    comm_df["food_basket_weight"] = comm_df["commodity_name"].map(COMMODITY_WEIGHTS).fillna(0.05)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_commodity;"))
        comm_df.to_sql("dim_commodity", con=conn, if_exists="append", index=False)

    # 3. dim_county_market
    market_df = df[["market_name", "sub_county", "county", "latitude", "longitude"]].drop_duplicates(subset=["market_name"]).copy()
    market_df = market_df.rename(columns={"county": "county_name"})
    market_df["region"] = market_df["county_name"].map(COUNTY_REGION_MAP).fillna("Other")
    market_df = market_df.sort_values(by="market_name")
    market_df["market_key"] = range(1, len(market_df) + 1)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_county_market;"))
        market_df.to_sql("dim_county_market", con=conn, if_exists="append", index=False)

    # 4. dim_date
    dates_s = pd.to_datetime(df["date_normalized"]).drop_duplicates().sort_values()
    date_records = []
    for dt in dates_s:
        date_records.append({
            "date_key": int(dt.strftime("%Y%m%d")),
            "full_date": dt.date(),
            "year": dt.year,
            "quarter": dt.quarter,
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "is_harvest_season": dt.month in [10, 11, 12],
        })
    date_dim_df = pd.DataFrame(date_records)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_date;"))
        date_dim_df.to_sql("dim_date", con=conn, if_exists="append", index=False)

    logger.info("Conformed dimensions populated successfully.")


def load_fact_table(df: pd.DataFrame, engine: Engine, if_exists: str = "append") -> int:
    init_warehouse(engine)
    populate_dimensions(df, engine)

    with engine.connect() as conn:
        dim_comm = pd.read_sql("SELECT commodity_key, commodity_name FROM dim_commodity", conn)
        dim_market = pd.read_sql("SELECT market_key, market_name FROM dim_county_market", conn)
        dim_date = pd.read_sql("SELECT date_key, full_date FROM dim_date", conn)
        dim_pt = pd.read_sql("SELECT price_type_key, price_type_name FROM dim_price_type", conn)

    df_fact = df.copy()
    df_fact["full_date"] = pd.to_datetime(df_fact["date_normalized"]).dt.date.astype(str)
    dim_date["full_date"] = dim_date["full_date"].astype(str)

    df_fact = df_fact.merge(dim_comm, left_on="commodity", right_on="commodity_name", how="left")
    df_fact = df_fact.merge(dim_market, on="market_name", how="left")
    df_fact = df_fact.merge(dim_pt, left_on="price_type", right_on="price_type_name", how="left")
    df_fact = df_fact.merge(dim_date, on="full_date", how="left")

    df_fact["price_id"] = range(1, len(df_fact) + 1)

    fact_cols = [
        "price_id",
        "date_key",
        "commodity_key",
        "market_key",
        "price_type_key",
        "raw_price",
        "raw_unit",
        "normalized_price_kes",
        "normalized_unit",
        "mom_inflation_pct",
        "yoy_inflation_pct",
        "data_quality_flag",
        "ingested_at",
    ]
    fact_table_df = df_fact[fact_cols].copy()

    with engine.begin() as conn:
        if if_exists == "replace":
            conn.execute(text("DELETE FROM fact_food_price;"))
        fact_table_df.to_sql(
            "fact_food_price",
            con=conn,
            if_exists="append",
            index=False,
            chunksize=1000,
        )

    logger.info("Loaded %d fact records into 'fact_food_price' (mode: %s).", len(fact_table_df), if_exists)
    return len(fact_table_df)
