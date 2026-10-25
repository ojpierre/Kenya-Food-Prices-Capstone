import os
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.warehouse import get_engine

st.set_page_config(
    page_title="Kenya Food Prices & Inflation Platform",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=600)
def load_data():
    engine = get_engine()
    query = """
    SELECT 
        f.price_id,
        d.full_date,
        d.year,
        d.month,
        d.month_name,
        d.is_harvest_season,
        c.commodity_name,
        c.category,
        c.standard_unit,
        m.market_name,
        m.county_name,
        m.region,
        m.latitude,
        m.longitude,
        p.price_type_name,
        f.raw_price,
        f.raw_unit,
        f.normalized_price_kes,
        f.normalized_unit,
        f.mom_inflation_pct,
        f.yoy_inflation_pct,
        f.data_quality_flag
    FROM fact_food_price f
    JOIN dim_commodity c ON f.commodity_key = c.commodity_key
    JOIN dim_county_market m ON f.market_key = m.market_key
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_price_type p ON f.price_type_key = p.price_type_key
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            df["full_date"] = pd.to_datetime(df["full_date"])
            return df
    except Exception as exc:
        st.error(f"Error querying database: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_lineage():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM etl_batch_lineage ORDER BY recorded_at DESC", conn)
    except Exception:
        return pd.DataFrame()


df = load_data()

st.title("???? Kenya Food Prices & Inflation Analytics Platform")
st.markdown(
    "A continuous data engineering platform monitoring staple commodity pricing, seasonal volatility, "
    "and regional inflation disparities across Kenyan counties and wholesale/retail channels."
)

if df.empty:
    st.warning("No warehouse data found. Please run the ETL pipeline first via python src/main.py.")
    st.stop()

# Sidebar Filters
st.sidebar.header("?? Analytical Filters")
all_commodities = sorted(df["commodity_name"].unique())
selected_commodities = st.sidebar.multiselect(
    "Select Commodities:",
    options=all_commodities,
    default=["Maize (white)", "Beans (rose coco)", "Cooking Oil"],
)

all_regions = sorted(df["region"].unique())
selected_regions = st.sidebar.multiselect(
    "Select Regions:",
    options=all_regions,
    default=all_regions,
)

channel_filter = st.sidebar.radio(
    "Market Channel:",
    options=["Retail", "Wholesale", "All Channels"],
    index=0,
)

filtered_df = df[
    (df["commodity_name"].isin(selected_commodities)) &
    (df["region"].isin(selected_regions))
]

if channel_filter != "All Channels":
    filtered_df = filtered_df[filtered_df["price_type_name"] == channel_filter]

# Top KPI Metric Cards
col1, col2, col3, col4 = st.columns(4)
latest_date = df["full_date"].max()
latest_df = df[df["full_date"] == latest_date]

avg_latest_price = latest_df["normalized_price_kes"].mean()
avg_latest_mom = latest_df["mom_inflation_pct"].mean()
avg_latest_yoy = latest_df["yoy_inflation_pct"].mean()
markets_count = df["market_name"].nunique()

col1.metric("Avg Unit Price (Latest)", f"KES {avg_latest_price:.2f}")
col2.metric("Headline MoM Inflation", f"{avg_latest_mom:+.1f}%")
col3.metric("Headline YoY Inflation", f"{avg_latest_yoy:+.1f}%")
col4.metric("Active Monitored Markets", f"{markets_count} Markets")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "?? Price Trajectories",
    "??? Regional & County Disparities",
    "?? Inflation Trends (MoM & YoY)",
    "?? Retail vs Wholesale Margins",
    "??? Data Lineage & Governance",
])

with tab1:
    st.subheader("Historical Price Trends Across Key Staple Commodities")
    ts_df = filtered_df.groupby(["full_date", "commodity_name"])["normalized_price_kes"].mean().reset_index()
    fig_ts = px.line(
        ts_df,
        x="full_date",
        y="normalized_price_kes",
        color="commodity_name",
        labels={"normalized_price_kes": "Price (KES per Standard Unit)", "full_date": "Observation Date"},
        title="Monthly Average Unit Price in KES (Normalized per 1 KG / 1 Liter)",
    )
    fig_ts.update_layout(hovermode="x unified", legend_title="Commodity")
    st.plotly_chart(fig_ts, use_container_width=True)

with tab2:
    st.subheader("County-Level Food Price Disparities")
    county_df = filtered_df.groupby(["county_name", "region", "commodity_name"])["normalized_price_kes"].mean().reset_index()
    fig_bar = px.bar(
        county_df,
        x="county_name",
        y="normalized_price_kes",
        color="commodity_name",
        barmode="group",
        labels={"county_name": "County", "normalized_price_kes": "Average Price (KES)"},
        title="Commodity Price Variations Across Counties",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Market Geospatial Distribution")
    geo_df = filtered_df[["market_name", "county_name", "latitude", "longitude", "normalized_price_kes"]].dropna().groupby(
        ["market_name", "county_name", "latitude", "longitude"]
    )["normalized_price_kes"].mean().reset_index()
    fig_map = px.scatter_mapbox(
        geo_df,
        lat="latitude",
        lon="longitude",
        size="normalized_price_kes",
        color="normalized_price_kes",
        color_continuous_scale="Viridis",
        hover_name="market_name",
        hover_data={"county_name": True, "normalized_price_kes": ":.2f"},
        zoom=5.5,
        center={"lat": 0.5, "lon": 37.8},
        mapbox_style="carto-positron",
        title="Market Monitoring Stations by Price Intensity",
    )
    st.plotly_chart(fig_map, use_container_width=True)

with tab3:
    st.subheader("Monthly (MoM) and Annual (YoY) Inflation Analysis")
    col_inf1, col_inf2 = st.columns(2)
    inf_df = filtered_df.groupby(["full_date", "commodity_name"])[["mom_inflation_pct", "yoy_inflation_pct"]].mean().reset_index()

    with col_inf1:
        fig_mom = px.line(
            inf_df,
            x="full_date",
            y="mom_inflation_pct",
            color="commodity_name",
            labels={"mom_inflation_pct": "MoM Inflation (%)"},
            title="Month-over-Month Price Change Rate (%)",
        )
        st.plotly_chart(fig_mom, use_container_width=True)

    with col_inf2:
        fig_yoy = px.line(
            inf_df,
            x="full_date",
            y="yoy_inflation_pct",
            color="commodity_name",
            labels={"yoy_inflation_pct": "YoY Inflation (%)"},
            title="Year-over-Year Annualized Inflation Rate (%)",
        )
        st.plotly_chart(fig_yoy, use_container_width=True)

with tab4:
    st.subheader("Retail vs Wholesale Distributor Spread")
    spread_pivot = df.pivot_table(
        index=["full_date", "commodity_name"],
        columns="price_type_name",
        values="normalized_price_kes",
        aggfunc="mean",
    ).reset_index()

    if "Retail" in spread_pivot.columns and "Wholesale" in spread_pivot.columns:
        spread_pivot["spread_kes"] = spread_pivot["Retail"] - spread_pivot["Wholesale"]
        spread_pivot["markup_pct"] = (spread_pivot["spread_kes"] / spread_pivot["Wholesale"]) * 100

        fig_spread = px.line(
            spread_pivot[spread_pivot["commodity_name"].isin(selected_commodities)],
            x="full_date",
            y="markup_pct",
            color="commodity_name",
            labels={"markup_pct": "Retail Markup (%)", "full_date": "Date"},
            title="Retail Channel Markup Over Wholesale (%)",
        )
        st.plotly_chart(fig_spread, use_container_width=True)

with tab5:
    st.subheader("Data Governance & Pipeline Lineage Ledger")
    lineage_df = load_lineage()
    if not lineage_df.empty:
        st.dataframe(lineage_df, use_container_width=True)
    else:
        st.info("No audit ledger runs logged yet.")
