import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tomllib
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import matplotlib.pyplot as plt
import statsmodels.api as sm
import datetime as dt


st.set_page_config(page_title="Forecasting of energy production and consumption")

st.title("Forecasting of energy production and consumption")

if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"

# Data loading functions
@st.cache_data(ttl=6000)
def load_mongo_data():
    with open(".streamlit/secrets.toml", "rb") as f:
        cfg = tomllib.load(f)

    PWD = cfg["MongoDB"]["pwd"]

    uri = f"mongodb+srv://esksko:{PWD}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority&appName=IND320-esksko"

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["IND320_assignment_4"]

    # Loading production data
    prod_data = list(db["production_data"].find())
    df_production = pd.DataFrame(prod_data)

    # Loading consumption data
    cons_data = list(db["consumption_data"].find())
    df_consumption = pd.DataFrame(cons_data)

    # Convert timestamps
    for df in (df_production, df_consumption):
        if "starttime" in df.columns:
            df["starttime"] = pd.to_datetime(df["starttime"])

    return df_production, df_consumption


# Cached MongoDB fetch
if "mongo_data" not in st.session_state:
    df_production, df_consumption = load_mongo_data()
    st.session_state["mongo_data"] = df_production, df_consumption
    st.write("Reading new data")
else:
    df_production, df_consumption = st.session_state["mongo_data"]
    st.write("Using cached data")


# UI Elements
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.subheader("Target Variable")

    dataset = st.radio("Select Energy Dataset", ("production", "consumption"), horizontal=True)
    df_energy = df_production if dataset == "production" else df_consumption

    price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    selected_area = st.radio("Select Price Area", 
                             price_areas,
                             index=price_areas.index(st.session_state["selected_area"])
                             )
    
    st.session_state["selected_area"] = selected_area

    if dataset == "production":
        energy_group = st.selectbox("Select Production Type", ["hydro", "wind", "solar", "thermal", "other"])
    elif dataset == "consumption":
        energy_group = st.selectbox("Select Consumption Type", ["primary", "secondary", "household", "cabin", "tertiary"])

with c2:
    MIN_DATE = dt.date(2021, 1, 1)
    MAX_DATE = dt.date(2024, 12, 31)
    TEMP_DATE = dt.date(2021, 12, 31)

    st.subheader("Training & Forecast")
    train_start = st.date_input("Training start", value=MIN_DATE, min_value=MIN_DATE, max_value=MAX_DATE)
    train_end = st.date_input("Training end", value=TEMP_DATE, min_value=MIN_DATE, max_value=MAX_DATE)

    if train_end < train_start:
        st.error("Error: End date must fall after start date.")

    forecast_horizon = st.number_input("Forecast horizon (hours)", 1, 1000, 168)

with c3:
    st.subheader("SARIMAX Parameters")

    p = st.number_input("p", 0, 5, 1)
    d = st.number_input("d", 0, 2, 1)
    q = st.number_input("q", 0, 5, 1)

with c4:
    st.subheader("Seasonal Order")

    P = st.number_input("P", 0, 3, 1)
    D = st.number_input("D", 0, 2, 1)
    Q = st.number_input("Q", 0, 3, 1)
    s = st.number_input("Seasonal period (s)", 1, 8760, 24)

# Choosing exogenous variables
exog_list = []
try:
    # pivot to wide columns like "group_pricearea"
    if dataset == "production":
        pivot = (
            df_energy
            .reset_index()
            .pivot_table(index="starttime", columns=["productiongroup", "pricearea"],
                         values="quantitykwh", aggfunc="mean")
        )
    else:
        pivot = (
            df_energy
            .reset_index()
            .pivot_table(index="starttime", columns=["consumptiongroup", "pricearea"],
                         values="quantitykwh", aggfunc="mean")
        )

    cols = [f"{grp}_{area}" for grp, area in pivot.columns]

    target_col = f"{energy_group}_{selected_area}"

    other_groups_same_area = [
        c for c in cols if c.endswith(f"_{selected_area}") and c != target_col
    ]

    same_group_other_areas = [
        c for c in cols if c.startswith(f"{energy_group}_") and not c.endswith(f"_{selected_area}")
    ]

    exog_list = other_groups_same_area + same_group_other_areas

except Exception:
    exog_list = []


exog_vars = st.multiselect("Exogenous variables (simultaneous categories)", exog_list)


# --- RUN BUTTON ---
run_model = st.button("Run Forecast")


if run_model:
    # --- Build wide-format hourly table for target + exog candidates ---
    # pivot to have columns like "group_pricearea"
    if dataset == "production":
        df_wide = (
            df_production
            .reset_index()
            .pivot_table(index="starttime", columns=["productiongroup", "pricearea"], values="quantitykwh", aggfunc="mean")
        )
    else:
        df_wide = (
            df_consumption
            .reset_index()
            .pivot_table(index="starttime", columns=["consumptiongroup", "pricearea"], values="quantitykwh", aggfunc="mean")
        )

    # flatten columns and ensure hourly index
    df_wide.columns = [f"{grp}_{area}" for grp, area in df_wide.columns]
    df_wide = df_wide.sort_index().asfreq("H")

    # Basic NaN handling (short gaps)
    df_wide = df_wide.ffill().interpolate(limit=24)

    # Define target column and check it exists
    target_col = f"{energy_group}_{selected_area}"
    if target_col not in df_wide.columns:
        st.error(f"Target column {target_col} not found in data.")
        st.stop()

    # Convert date inputs to datetimes covering the whole day of train_end
    train_start_dt = pd.to_datetime(train_start)
    train_end_dt = pd.to_datetime(train_end) + pd.Timedelta(hours=23, minutes=59, seconds=59)

    # Slice y (target) for training
    y = df_wide[target_col].loc[train_start_dt:train_end_dt].copy()
    if y.empty:
        st.error("No training data available for the selected date range and filters.")
        st.stop()

    # Build exog_train from selected exog_vars (only keep columns that actually exist)
    chosen_exogs = [v for v in exog_vars if v in df_wide.columns]
    if chosen_exogs:
        exog_train = df_wide[chosen_exogs].loc[train_start_dt:train_end_dt].copy()
        # Ensure alignment and handle remaining NaNs
        exog_train = exog_train.ffill().interpolate(limit=24).fillna(method="bfill").fillna(0)
    else:
        exog_train = None

    # Fit SARIMAX with exogenous variables if provided
    model = sm.tsa.statespace.SARIMAX(
        y,
        exog=exog_train,
        order=(p, d, q),
        seasonal_order=(P, D, Q, s),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    try:
        results = model.fit(disp=False)
    except Exception as e:
        st.error(f"Model fitting failed: {e}")
        st.stop()

    with st.expander("Model Summary"):
        st.text(results.summary().as_text())

    # Forecast: prepare exog_future for H steps
    H = int(forecast_horizon)
    last_index = y.index[-1]
    future_index = pd.date_range(start=last_index + pd.Timedelta(hours=1), periods=H, freq="H")

    if chosen_exogs:
        # Option 1 (naive): repeat last observed exog row
        last_exog = df_wide[chosen_exogs].loc[:train_end_dt].iloc[-1]
        exog_future = pd.DataFrame([last_exog.values] * H, columns=chosen_exogs, index=future_index)     
    else:
        exog_future = None

    # Get forecast using exog_future (if any)
    forecast_res = results.get_forecast(steps=H, exog=exog_future)
    forecast_mean = forecast_res.predicted_mean
    forecast_ci = forecast_res.conf_int()

    # --- Plot (same layout as before) ---
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=y.index, y=y.values,
        mode="lines", name="Training data"
    ))

    fig.add_trace(go.Scatter(
        x=forecast_mean.index, y=forecast_mean.values,
        mode="lines", name="Forecast"
    ))

    fig.add_trace(go.Scatter(
        x=forecast_ci.index, y=forecast_ci.iloc[:, 0],
        mode="lines", line=dict(width=0), showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=forecast_ci.index, y=forecast_ci.iloc[:, 1],
        mode="lines", fill="tonexty", line=dict(width=0),
        name="Confidence Interval"
    ))

    st.plotly_chart(fig, use_container_width=True)
