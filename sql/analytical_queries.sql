-- Analytical Queries answering Food Security and Inflation Questions

-- 1. Top Food Commodities with Highest Year-over-Year (YoY) Inflation
SELECT 
    c.commodity_name,
    c.category,
    d.year,
    d.month_name,
    ROUND(AVG(f.normalized_price_kes), 2) AS avg_price_kes,
    ROUND(AVG(f.yoy_inflation_pct), 2) AS avg_yoy_inflation_pct
FROM fact_food_price f
JOIN dim_commodity c ON f.commodity_key = c.commodity_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2024 AND d.month = 12 AND f.price_type_key = 1
GROUP BY c.commodity_name, c.category, d.year, d.month_name
ORDER BY avg_yoy_inflation_pct DESC;

-- 2. Regional Price Disparity: White Maize Across Kenyan Counties
SELECT 
    m.county_name,
    m.region,
    ROUND(AVG(f.normalized_price_kes), 2) AS avg_maize_price_per_kg,
    ROUND(MIN(f.normalized_price_kes), 2) AS min_price_kes,
    ROUND(MAX(f.normalized_price_kes), 2) AS max_price_kes
FROM fact_food_price f
JOIN dim_commodity c ON f.commodity_key = c.commodity_key
JOIN dim_county_market m ON f.market_key = m.market_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE c.commodity_name LIKE '%Maize%' AND d.year = 2024
GROUP BY m.county_name, m.region
ORDER BY avg_maize_price_per_kg DESC;

-- 3. Retail vs Wholesale Price Margins by Commodity
SELECT 
    c.commodity_name,
    d.year,
    ROUND(AVG(CASE WHEN p.price_type_name = 'Retail' THEN f.normalized_price_kes END), 2) AS retail_avg,
    ROUND(AVG(CASE WHEN p.price_type_name = 'Wholesale' THEN f.normalized_price_kes END), 2) AS wholesale_avg,
    ROUND(AVG(CASE WHEN p.price_type_name = 'Retail' THEN f.normalized_price_kes END) - 
          AVG(CASE WHEN p.price_type_name = 'Wholesale' THEN f.normalized_price_kes END), 2) AS spread_kes,
    ROUND(((AVG(CASE WHEN p.price_type_name = 'Retail' THEN f.normalized_price_kes END) - 
            AVG(CASE WHEN p.price_type_name = 'Wholesale' THEN f.normalized_price_kes END)) / 
            AVG(CASE WHEN p.price_type_name = 'Wholesale' THEN f.normalized_price_kes END)) * 100, 2) AS markup_pct
FROM fact_food_price f
JOIN dim_commodity c ON f.commodity_key = c.commodity_key
JOIN dim_price_type p ON f.price_type_key = p.price_type_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2024
GROUP BY c.commodity_name, d.year
ORDER BY spread_kes DESC;

-- 4. Harvest Season vs Non-Harvest Season Price Volatility
SELECT 
    c.commodity_name,
    CASE WHEN d.is_harvest_season THEN 'Harvest Season (Oct-Dec)' ELSE 'Lean/Planting Season (Jan-Sep)' END AS seasonal_period,
    ROUND(AVG(f.normalized_price_kes), 2) AS avg_price_kes,
    ROUND(AVG(f.mom_inflation_pct), 2) AS avg_mom_inflation_pct
FROM fact_food_price f
JOIN dim_commodity c ON f.commodity_key = c.commodity_key
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY c.commodity_name, seasonal_period
ORDER BY c.commodity_name, seasonal_period;

-- 5. National Weighted Food Basket Inflation Index
SELECT 
    d.year,
    d.month,
    d.month_name,
    ROUND(SUM(f.normalized_price_kes * c.food_basket_weight), 2) AS weighted_food_basket_cost_kes,
    ROUND(AVG(f.yoy_inflation_pct), 2) AS headline_food_inflation_yoy
FROM fact_food_price f
JOIN dim_commodity c ON f.commodity_key = c.commodity_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.price_type_key = 1 -- Retail
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;
