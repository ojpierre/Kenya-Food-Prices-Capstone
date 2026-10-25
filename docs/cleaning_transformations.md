# Milestone 3: Cleaning and Normalisation Evidence

This document provides before-and-after examples demonstrating each data cleansing and standardisation rule implemented in src/transformation.py.

---

## Transformation 1: Packaging Unit Standardisation

### Problem
Raw grain commodities are reported in heterogeneous package sizes (e.g. 90 KG bag, 50 KG bag, 1 KG), making direct price comparisons impossible. A 90 KG bag of Maize listed at KES 4,500 would mistakenly look 90x more expensive than a 1 KG pack at KES 60.

### Before
| commodity | raw_unit | raw_price (KES) |
|---|---|---|
| Maize (white) | 90 KG bag | 4,500.00 |
| Maize (white) | 1 KG | 55.00 |
| Cooking Oil | 500 ML | 145.00 |
| Cooking Oil | 1 L | 280.00 |

### After
| commodity | normalized_unit | normalized_price_kes | unit_divisor |
|---|---|---|---|
| Maize (white) | KG | 50.00 | 90.0 |
| Maize (white) | KG | 55.00 | 1.0 |
| Cooking Oil | L | 290.00 | 0.5 |
| Cooking Oil | L | 280.00 | 1.0 |

---

## Transformation 2: Missing Administrative Sub-County Imputation

### Problem
Approximately 5% of raw records omit the dmin2 (sub-county) attribute, breaking regional grouping hierarchies.

### Before
| market_name | county | sub_county |
|---|---|---|
| Gikomba | Nairobi | NaN |
| Kongowea | Mombasa | None |
| Kibuye | Kisumu |   |

### After
| market_name | county | sub_county |
|---|---|---|
| Gikomba | Nairobi | **Starehe** |
| Kongowea | Mombasa | **Nyali** |
| Kibuye | Kisumu | **Kisumu Central** |

---

## Transformation 3: Missing Local Currency Price Recovery

### Problem
Occasional records lack the primary price (KES) column but contain the usdprice exchange estimate.

### Before
| commodity | price (KES) | usdprice |
|---|---|---|
| Beans (rose coco) | NaN | 1.05 |

### After
| commodity | raw_price (KES) | usd_price | imputed_flag |
|---|---|---|---|
| Beans (rose coco) | **141.75** (1.05 * 135) | 1.05 | Recovered |

---

## Transformation 4: Temporal Alignment and Inflation Indexing

### Problem
Observations are captured mid-month (e.g. 2023-04-15), hindering consistent calendar joins, and lack direct inflation metrics.

### Before
| date | commodity | normalized_price_kes |
|---|---|---|
| 2023-04-15 | Maize (white) | 65.00 |
| 2023-05-15 | Maize (white) | 71.50 |
| 2024-05-15 | Maize (white) | 58.00 |

### After
| date_normalized | commodity | normalized_price_kes | mom_inflation_pct | yoy_inflation_pct |
|---|---|---|---|---|
| 2023-04-01 | Maize (white) | 65.00 | NaN | NaN |
| 2023-05-01 | Maize (white) | 71.50 | **+10.00%** | NaN |
| 2024-05-01 | Maize (white) | 58.00 | -4.20% | **-18.88%** |

---

## Transformation 5: Statistical Outlier Flagging

### Problem
Data anomalies or severe crisis spikes distort ordinary aggregation. Rather than silently deleting valid economic shock records, the pipeline flags records based on Interquartile Range (IQR).

### Before
| commodity | normalized_price_kes |
|---|---|
| Cabbage | 42.00 |
| Cabbage | 480.00 (data entry error) |

### After
| commodity | normalized_price_kes | data_quality_flag |
|---|---|---|
| Cabbage | 42.00 | **VALID** |
| Cabbage | 480.00 | **OUTLIER** |
