import random
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd

MARKETS = [
    {"market": "Gikomba", "admin1": "Nairobi", "admin2": "Starehe", "region": "Nairobi", "lat": -1.2864, "lon": 36.8372},
    {"market": "Muthurwa", "admin1": "Nairobi", "admin2": "Kamukunji", "region": "Nairobi", "lat": -1.2889, "lon": 36.8344},
    {"market": "Kongowea", "admin1": "Mombasa", "admin2": "Nyali", "region": "Coast", "lat": -4.0435, "lon": 39.6682},
    {"market": "Kibuye", "admin1": "Kisumu", "admin2": "Kisumu Central", "region": "Nyanza", "lat": -0.1022, "lon": 34.7617},
    {"market": "Nakuru Central", "admin1": "Nakuru", "admin2": "Nakuru East", "region": "Rift Valley", "lat": -0.3031, "lon": 36.0800},
    {"market": "Eldoret Main", "admin1": "Uasin Gishu", "admin2": "Ainabkoi", "region": "Rift Valley", "lat": 0.5143, "lon": 35.2698},
    {"market": "Nyeri Open Air", "admin1": "Nyeri", "admin2": "Nyeri Central", "region": "Central", "lat": -0.4201, "lon": 36.9476},
    {"market": "Garissa Main", "admin1": "Garissa", "admin2": "Garissa", "region": "North Eastern", "lat": -0.4532, "lon": 39.6461},
    {"market": "Lodwar Town", "admin1": "Turkana", "admin2": "Turkana Central", "region": "Rift Valley", "lat": 3.1191, "lon": 35.5973},
    {"market": "Machakos Town", "admin1": "Machakos", "admin2": "Machakos", "region": "Eastern", "lat": -1.5177, "lon": 37.2634},
]

COMMODITIES = [
    {"commodity": "Maize (white)", "category": "cereals and tubers", "base_price_kg": 45.0, "unit_options": [("1 KG", 1), ("90 KG bag", 90)], "weight": 0.25},
    {"commodity": "Beans (rose coco)", "category": "pulses and nuts", "base_price_kg": 110.0, "unit_options": [("1 KG", 1), ("90 KG bag", 90)], "weight": 0.15},
    {"commodity": "Potatoes (Irish)", "category": "cereals and tubers", "base_price_kg": 55.0, "unit_options": [("1 KG", 1), ("50 KG bag", 50)], "weight": 0.10},
    {"commodity": "Rice (imported)", "category": "cereals and tubers", "base_price_kg": 140.0, "unit_options": [("1 KG", 1), ("50 KG bag", 50)], "weight": 0.12},
    {"commodity": "Cooking Oil", "category": "oil and fats", "base_price_kg": 280.0, "unit_options": [("1 L", 1), ("500 ML", 0.5)], "weight": 0.10},
    {"commodity": "Cow Milk (fresh)", "category": "milk and dairy", "base_price_kg": 65.0, "unit_options": [("1 L", 1)], "weight": 0.08},
    {"commodity": "Bread (white)", "category": "cereals and tubers", "base_price_kg": 140.0, "unit_options": [("Loaf 400g", 0.4)], "weight": 0.06},
    {"commodity": "Sugar", "category": "food essentials", "base_price_kg": 130.0, "unit_options": [("1 KG", 1), ("50 KG bag", 50)], "weight": 0.08},
    {"commodity": "Sorghum", "category": "cereals and tubers", "base_price_kg": 75.0, "unit_options": [("1 KG", 1), ("90 KG bag", 90)], "weight": 0.03},
    {"commodity": "Cabbage", "category": "vegetables and fruits", "base_price_kg": 40.0, "unit_options": [("1 KG", 1)], "weight": 0.03},
]


def generate_benchmark_dataset(start_year: int = 2021, end_year: int = 2024) -> pd.DataFrame:
    random.seed(42)
    records: List[Dict[str, Any]] = []

    years = list(range(start_year, end_year + 1))
    months = list(range(1, 13))

    for year in years:
        for month in months:
            date_str = f"{year}-{month:02d}-15"
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # Inflation baseline multiplier reflecting Kenya's economic trajectory (2021-2024 food inflation)
            time_idx = (year - start_year) * 12 + month
            inflation_factor = 1.0 + (time_idx * 0.009)

            # Seasonal harvest shock (food cheaper in Oct-Dec, expensive in April-July)
            seasonal_factor = 0.93 if month in [10, 11, 12] else (1.08 if month in [4, 5, 6, 7] else 1.0)

            for mkt in MARKETS:
                # Regional transport and logistics markup (e.g. Turkana & Garissa higher prices than Nakuru/Eldoret)
                regional_mult = 1.25 if mkt["admin1"] in ["Turkana", "Garissa", "Marsabit"] else (
                    0.92 if mkt["admin1"] in ["Uasin Gishu", "Nakuru"] else 1.05
                )

                for comm in COMMODITIES:
                    unit_name, unit_mult = random.choice(comm["unit_options"])

                    for price_type in ["Retail", "Wholesale"]:
                        type_mult = 0.88 if price_type == "Wholesale" else 1.0
                        noise = random.uniform(0.96, 1.04)

                        unit_price_kes = comm["base_price_kg"] * inflation_factor * seasonal_factor * regional_mult * type_mult * noise
                        total_price_kes = round(unit_price_kes * unit_mult, 2)
                        usd_price = round(total_price_kes / 135.0, 2)

                        admin2_val = mkt["admin2"]
                        # Inject small percentage of missing admin2 to test data cleaning
                        if random.random() < 0.03:
                            admin2_val = None

                        record = {
                            "date": date_str,
                            "admin1": mkt["admin1"],
                            "admin2": admin2_val,
                            "market": mkt["market"],
                            "latitude": mkt["lat"],
                            "longitude": mkt["lon"],
                            "category": comm["category"],
                            "commodity": comm["commodity"],
                            "unit": unit_name,
                            "priceflag": "actual",
                            "pricetype": price_type,
                            "currency": "KES",
                            "price": total_price_kes,
                            "usdprice": usd_price,
                        }
                        records.append(record)

    df = pd.DataFrame(records)
    return df
