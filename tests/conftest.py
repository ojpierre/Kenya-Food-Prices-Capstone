from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "date": "2024-01-15",
            "market": "Nairobi - Marikiti",
            "latitude": -1.286389,
            "longitude": 36.817223,
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "90 KG bag",
            "priceflag": "actual",
            "pricetype": "Wholesale",
            "currency": "KES",
            "price": 5400.0,
            "usdprice": 36.0,
        },
        {
            "date": "2024-01-15",
            "market": "Nairobi - Marikiti",
            "latitude": -1.286389,
            "longitude": 36.817223,
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "1 KG",
            "priceflag": "actual",
            "pricetype": "Retail",
            "currency": "KES",
            "price": 70.0,
            "usdprice": 0.47,
        },
        {
            "date": "2024-02-15",
            "market": "Nairobi - Marikiti",
            "latitude": -1.286389,
            "longitude": 36.817223,
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "1 KG",
            "priceflag": "actual",
            "pricetype": "Retail",
            "currency": "KES",
            "price": 75.0,
            "usdprice": 0.50,
        },
        {
            "date": "2024-01-15",
            "market": "Mombasa - Kongowea",
            "latitude": -4.043477,
            "longitude": 39.668206,
            "category": "oil and fats",
            "commodity": "Cooking Oil",
            "unit": "500 ML",
            "priceflag": "actual",
            "pricetype": "Retail",
            "currency": "KES",
            "price": 180.0,
            "usdprice": 1.20,
        },
    ])


@pytest.fixture
def sqlite_test_engine(tmp_path: Path) -> Engine:
    db_file = (tmp_path / "test_warehouse.db").as_posix()
    return create_engine(f"sqlite:///{db_file}")
