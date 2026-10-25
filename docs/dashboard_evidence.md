# Milestone 7: Dashboard and Insights Evidence

## 1. Overview and Hosting Architecture

The analytical interface is implemented using **Streamlit** and **Plotly** in dashboard/app.py, directly connected to the analytical star schema warehouse.

- **App Command**: streamlit run dashboard/app.py
- **Dialect Supported**: PostgreSQL and SQLite
- **Interactive Capabilities**: Multi-commodity selector, regional/county filters, trading channel toggles (Retail vs Wholesale), and zoomable geospatial market maps.

---

## 2. Core Business and Economic Questions Answered

### Question 1: How have staple food prices evolved across Kenya over the past 4 years?
- **Visualization**: Interactive time-series line chart in Tab 1.
- **Insight**: Highlights price peaks during the 2022 drought and inflation shocks (e.g., Cooking Oil soaring above 380 KES/L and White Maize reaching 80 KES/KG), followed by post-harvest corrections.

### Question 2: Which counties face the highest food price premiums?
- **Visualization**: County price comparison bar chart and geospatial scatter map in Tab 2.
- **Insight**: Counties in Arid and Semi-Arid Lands (ASALs)—such as Turkana (Lodwar) and Garissa—experience 20% to 35% higher staple prices compared to Rift Valley agricultural hubs (Eldoret and Nakuru) due to inter-county logistics and transport friction.

### Question 3: How volatile are Month-over-Month (MoM) and Year-over-Year (YoY) food inflation rates?
- **Visualization**: Dual inflation index tracker in Tab 3.
- **Insight**: Reveals severe seasonal MoM price drops (-5% to -10%) coinciding with primary harvest months (October through December), contrasted with sharp spikes prior to the long rains harvest (April to July).

### Question 4: What is the markup between wholesale and retail prices?
- **Visualization**: Retail vs Wholesale margin tracker in Tab 4.
- **Insight**: Retail consumer prices average a 12% to 18% markup over bulk wholesale prices for dry staples, with perishable vegetables showing higher spreads (>25%).

### Question 5: How are data quality and governance verified?
- **Visualization**: Audit Ledger viewer in Tab 5.
- **Insight**: Displays live execution logs from etl_batch_lineage, verifying row counts and automated data quality assertion pass rates.
