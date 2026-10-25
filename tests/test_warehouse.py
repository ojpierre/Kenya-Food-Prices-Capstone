import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from src.transformation import clean_and_normalize_food_prices
from src.warehouse import init_warehouse, load_fact_table, populate_dimensions


def test_warehouse_initialization(sqlite_test_engine: Engine):
    init_warehouse(sqlite_test_engine)
    inspector = inspect(sqlite_test_engine)
    tables = inspector.get_table_names()
    assert "dim_commodity" in tables
    assert "dim_county_market" in tables
    assert "dim_date" in tables
    assert "dim_price_type" in tables
    assert "fact_food_price" in tables


def test_populate_dimensions_and_load_facts(sample_raw_df: pd.DataFrame, sqlite_test_engine: Engine):
    cleaned = clean_and_normalize_food_prices(sample_raw_df)
    rows_loaded = load_fact_table(cleaned, sqlite_test_engine, if_exists="replace")
    assert rows_loaded == len(cleaned)

    with sqlite_test_engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_food_price")).scalar()
        assert fact_count == len(cleaned)

        # Verify conformed join
        res = conn.execute(text("""
            SELECT f.price_id, c.commodity_name, m.market_name, p.price_type_name
            FROM fact_food_price f
            JOIN dim_commodity c ON f.commodity_key = c.commodity_key
            JOIN dim_county_market m ON f.market_key = m.market_key
            JOIN dim_price_type p ON f.price_type_key = p.price_type_key
        """)).fetchall()
        assert len(res) == len(cleaned)
