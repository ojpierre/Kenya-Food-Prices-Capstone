import pandas as pd
import pytest
from src.transformation import clean_and_normalize_food_prices


def test_unit_normalization_and_pricing(sample_raw_df: pd.DataFrame):
    cleaned = clean_and_normalize_food_prices(sample_raw_df)
    
    # 90 KG bag of Maize at 5400 KES should normalize to 60.0 KES / KG
    wholesale_row = cleaned[cleaned["raw_unit"] == "90 KG bag"].iloc[0]
    assert wholesale_row["normalized_unit"] == "KG"
    assert pytest.approx(wholesale_row["normalized_price_kes"], 0.01) == 60.0

    # 500 ML cooking oil at 180 KES should normalize to 360.0 KES / L
    oil_row = cleaned[cleaned["raw_unit"] == "500 ML"].iloc[0]
    assert oil_row["normalized_unit"] == "L"
    assert pytest.approx(oil_row["normalized_price_kes"], 0.01) == 360.0


def test_county_and_sub_county_resolution(sample_raw_df: pd.DataFrame):
    cleaned = clean_and_normalize_food_prices(sample_raw_df)
    
    nairobi_row = cleaned[cleaned["county"] == "Nairobi"].iloc[0]
    assert nairobi_row["sub_county"] == "Starehe"
    assert nairobi_row["market_name"] == "Marikiti"

    mombasa_row = cleaned[cleaned["county"] == "Mombasa"].iloc[0]
    assert mombasa_row["sub_county"] == "Nyali"
    assert mombasa_row["market_name"] == "Kongowea"


def test_currency_filtering():
    invalid_curr_df = pd.DataFrame([
        {
            "date": "2024-01-15",
            "market": "Nairobi - Marikiti",
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "1 KG",
            "pricetype": "Retail",
            "currency": "USD",
            "price": 0.5,
        }
    ])
    cleaned = clean_and_normalize_food_prices(invalid_curr_df)
    assert len(cleaned) == 0


def test_missing_and_negative_prices():
    bad_df = pd.DataFrame([
        {
            "date": "2024-01-15",
            "market": "Nairobi - Marikiti",
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "1 KG",
            "pricetype": "Retail",
            "currency": "KES",
            "price": -10.0,
        },
        {
            "date": "2024-01-15",
            "market": "Nairobi - Marikiti",
            "category": "cereals and tubers",
            "commodity": "Maize (white)",
            "unit": "1 KG",
            "pricetype": "Retail",
            "currency": "KES",
            "price": None,
        },
    ])
    cleaned = clean_and_normalize_food_prices(bad_df)
    assert len(cleaned) == 0
