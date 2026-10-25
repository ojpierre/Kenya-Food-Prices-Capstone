import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union
import numpy as np
import pandas as pd

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

MARKET_SUBCOUNTY_MAP = {
    "Marikiti": "Starehe",
    "Gikomba": "Starehe",
    "Muthurwa": "Kamukunji",
    "Kangemi": "Westlands",
    "Kongowea": "Nyali",
    "Majengo": "Mvita",
    "Kibuye": "Kisumu Central",
    "Jubilee": "Kisumu Central",
    "Nakuru Central": "Nakuru East",
    "Wakilishi": "Nakuru West",
    "Eldoret Main": "Ainabkoi",
    "Nyeri Open Air": "Nyeri Central",
    "Garissa Main": "Garissa",
    "Lodwar Town": "Turkana Central",
    "Marsabit Central": "Saku",
    "Machakos Town": "Machakos",
}

UNIT_CONVERSION_MAP = {
    "1 KG": (1.0, "KG"),
    "KG": (1.0, "KG"),
    "90 KG bag": (90.0, "KG"),
    "90 KG": (90.0, "KG"),
    "50 KG bag": (50.0, "KG"),
    "50 KG": (50.0, "KG"),
    "100 KG bag": (100.0, "KG"),
    "1 L": (1.0, "L"),
    "Liter": (1.0, "L"),
    "500 ML": (0.5, "L"),
    "Loaf 400g": (0.4, "KG"),
}


def _flag_outliers_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    df["data_quality_flag"] = "VALID"
    for comm in df["commodity"].unique():
        mask = df["commodity"] == comm
        prices = df.loc[mask, "normalized_price_kes"]
        if len(prices) >= 4:
            q1 = prices.quantile(0.25)
            q3 = prices.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - (2.0 * iqr)
            upper = q3 + (2.5 * iqr)
            outliers = mask & ((df["normalized_price_kes"] < lower) | (df["normalized_price_kes"] > upper))
            df.loc[outliers, "data_quality_flag"] = "OUTLIER"
    return df


def clean_and_normalize_food_prices(
    source: Union[pd.DataFrame, Path, str],
    output_path: Optional[Path] = None,
) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        logger.info("Loading raw food prices from %s", source)
        df = pd.read_csv(source, low_memory=False)
    elif isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        raise ValueError(f"Unsupported data source type: {type(source)}")

    initial_count = len(df)
    logger.info("Starting data cleaning and normalisation on %d records...", initial_count)

    rename_candidates = {
        "admin1": "county",
        "admin2": "sub_county",
        "market": "market_name",
        "price": "raw_price",
        "unit": "raw_unit",
        "pricetype": "price_type",
        "usdprice": "usd_price",
    }
    df = df.rename(columns=rename_candidates)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        return pd.DataFrame()

    df = df.dropna(subset=["date", "commodity", "market_name"])
    df["date_normalized"] = df["date"].dt.to_period("M").dt.to_timestamp()

    if "county" not in df.columns:
        df["county"] = df["market_name"].apply(
            lambda m: str(m).split(" - ")[0].strip() if " - " in str(m) else "Nairobi"
        )
    df["county"] = df["county"].astype(str).str.strip().str.title()

    df["market_name"] = df["market_name"].apply(
        lambda m: str(m).split(" - ")[1].strip() if " - " in str(m) else str(m).strip()
    )

    if "sub_county" not in df.columns:
        df["sub_county"] = None

    df["sub_county"] = df.apply(
        lambda r: MARKET_SUBCOUNTY_MAP.get(r["market_name"], r["sub_county"])
        if pd.isna(r["sub_county"]) or str(r["sub_county"]).strip() in ["", "None", "nan"]
        else str(r["sub_county"]).strip(),
        axis=1,
    )

    if "currency" in df.columns:
        df["currency"] = df["currency"].fillna("KES").astype(str).str.upper()
        df = df[df["currency"] == "KES"]
    else:
        df["currency"] = "KES"

    df["raw_price"] = pd.to_numeric(df["raw_price"], errors="coerce")
    if "usd_price" in df.columns:
        df["usd_price"] = pd.to_numeric(df["usd_price"], errors="coerce")
        df["raw_price"] = df["raw_price"].fillna(df["usd_price"] * 135.0)

    df = df.dropna(subset=["raw_price"])
    df = df[df["raw_price"] > 0]

    if len(df) == 0:
        return pd.DataFrame(columns=[
            "date_normalized", "commodity", "category", "market_name", "county", "sub_county",
            "price_type", "raw_price", "raw_unit", "normalized_price_kes", "normalized_unit",
            "mom_inflation_pct", "yoy_inflation_pct", "data_quality_flag", "ingested_at"
        ])

    def _convert_unit(row: pd.Series):
        unit_str = str(row.get("raw_unit", "1 KG")).strip()
        divisor, norm_unit = UNIT_CONVERSION_MAP.get(unit_str, (1.0, "KG"))
        norm_price = round(float(row["raw_price"]) / divisor, 2)
        return pd.Series([norm_price, norm_unit])

    df[["normalized_price_kes", "normalized_unit"]] = df.apply(_convert_unit, axis=1)

    df = df.sort_values(
        by=["commodity", "market_name", "price_type", "date_normalized"],
        ascending=True,
    )

    df["lag_1m_price"] = df.groupby(["commodity", "market_name", "price_type"])["normalized_price_kes"].shift(1)
    df["mom_inflation_pct"] = (
        (df["normalized_price_kes"] - df["lag_1m_price"]) / df["lag_1m_price"] * 100.0
    ).round(2)

    df["lag_12m_price"] = df.groupby(["commodity", "market_name", "price_type"])["normalized_price_kes"].shift(12)
    df["yoy_inflation_pct"] = (
        (df["normalized_price_kes"] - df["lag_12m_price"]) / df["lag_12m_price"] * 100.0
    ).round(2)

    df = df.drop(columns=["lag_1m_price", "lag_12m_price"])

    df = _flag_outliers_vectorized(df)

    df["ingested_at"] = datetime.now(timezone.utc)

    df = df.drop_duplicates(
        subset=["date_normalized", "commodity", "market_name", "price_type"],
        keep="last",
    )
    df = df.reset_index(drop=True)

    dest_path = output_path or (settings.processed_data_dir / "kenya_food_prices_cleaned.csv")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest_path, index=False)

    logger.info("Cleaned %d records successfully (saved to %s).", len(df), dest_path)
    return df
