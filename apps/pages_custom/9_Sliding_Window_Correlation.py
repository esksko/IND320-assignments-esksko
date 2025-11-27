import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import tomllib
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import matplotlib.pyplot as plt


st.set_page_config(page_title="Sliding Window Correlation")

st.title("Sliding-Window Correlation Explorer")

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



@st.cache_data(ttl=6000)
def load_data_from_api(lat, lon, year, variables=None):
    if variables is None:
        variables = ["temperature_2m", "precipitation", "wind_speed_10m", 
                     "wind_gusts_10m", "wind_direction_10m"]

    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly="
    )
    url += ",".join(variables)
    url += "&timezone=Europe%2FOslo"

    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"Failed to load data: {response.status_code}")
        return None

    data = response.json()
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def sliding_correlation(df, window_hours) -> pd.DataFrame:
    
    df_corr = df["quantitykwh"].rolling(window=window_hours).corr(df["meteo"])
    df_corr = pd.DataFrame({"time": df.index, "corr": df_corr})
    return df_corr


# Checking if MongoDB data is already loaded
if "mongo_data" not in st.session_state:
    df_production, df_consumption = load_mongo_data()
    st.session_state["mongo_data"] = df_production, df_consumption
    st.write("Reading new data")
else:
    df_production, df_consumption = st.session_state["mongo_data"]
    st.write("Using cached data")



# User selections


if "clicked_coord" not in st.session_state:
    st.warning("No coordinate selected on the map page.\nGo to the map page and click on the map first.")
    st.stop()


st.subheader("Settings")

lat, lon = st.session_state["clicked_coord"]





c1, c2 = st.columns(2)


# Selectors
with c1:
    selected_year = st.radio("Year", [2021, 2022, 2023, 2024], index=0, horizontal=True)
    selected_pricearea = st.radio("Price Area", ["NO1", "NO2", "NO3", "NO4", "NO5"], index=0, horizontal=True)
    energy_var = st.radio("Energy Variable", ["production", "consumption"], index=0, horizontal=True)
    
    met_var = st.selectbox(
        "Select meteorological variable for correlation:",
        ["temperature_2m", "precipitation", "wind_speed_10m", 
        "wind_gusts_10m", "wind_direction_10m"])
    
    
    
with c2:
    window = st.slider("Select sliding window size (hours):", 24, 720, 168)
    lag = st.slider("Lag (hours)", -168, 168, 0)
    center = st.slider("Center index for highlighting:", 0, 8760, 4380)





# Getting data into dataframes and merging
df_meteorological = load_data_from_api(lat, lon, selected_year, variables=[met_var])
df_energy = df_production if energy_var == "production" else df_consumption

# Cleaning energy data for merging
df_energy = df_energy[(df_energy["pricearea"] == selected_pricearea) & (df_energy["starttime"].dt.year == selected_year)]
df_energy = df_energy.groupby("starttime")["quantitykwh"].sum().reset_index() 
df_energy.rename(columns={"starttime": "time"}, inplace=True)

df_meteorological.rename(columns={met_var: "meteo"}, inplace=True)

# Merging dataframes on time

df_merged = pd.merge(df_meteorological[["time", "meteo"]],
                     df_energy[["time", "quantitykwh"]],
                     on="time",
                     how="inner")


df_merged = df_merged.set_index("time").sort_index()
df_merged = df_merged.reset_index(drop=True)


# Applying lag
df_merged["meteo_lagged"] = df_merged["meteo"].shift(lag)


def plotly_lagged_correlation(df, lag=0, window=45, center=200):

    # Extract series
    energy = df["quantitykwh"].reset_index(drop=True)
    meteo  = df["meteo"].reset_index(drop=True)

    time_index = df.index

    # Apply lag
    meteo_lagged = meteo.shift(lag)

    # Sliding window correlation
    swc = energy.rolling(window, center=True).corr(meteo_lagged)

    # Plotting
    fig = make_subplots(
        rows=3, 
        cols=1, 
        shared_xaxes=False,
        subplot_titles=(
            f"{met_var} (lagged by {lag} hours)",
            f"{energy_var} (kWh)",
            "Sliding Window Correlation")
        )

    fig.update_layout(
        height=1700, 
        title_text="Lagged Sliding Window Correlation",
        showlegend=False,
        )
    
    for r in range(1, 4):
        fig.update_xaxes(title_text="Hours", row=r, col=1)

    # Meteorology plot
    fig.add_trace(
        go.Scatter(
            x=list(range(len(meteo))),
            y=meteo,
            mode="lines",
            name=f"{met_var} (lag={lag})",
        ),
        row=1, col=1
    )

    # Compute highlighted window
    start_lag = max(0, center - window//2 + lag)
    end_lag   = min(len(meteo), center + window//2 + lag)

    fig.add_trace(
        go.Scatter(
            x=list(range(start_lag, end_lag)),
            y=meteo[start_lag:end_lag],
            mode="lines",
            line=dict(color="red", width=4),
            name="Lag Highlight"
        ),
        row=1, col=1
    )


    # Energy plot

    fig.add_trace(
        go.Scatter(
            x=energy.index,
            y=energy,
            mode="lines",
            name=f"{energy_var} (kWh)"
        ),
        row=2, col=1
    )

    start_w = max(0, center - window//2)
    end_w   = min(len(energy), center + window//2)

    fig.add_trace(
        go.Scatter(
            x=list(range(start_w, end_w)),
            y=energy[start_w:end_w],
            mode="lines",
            line=dict(color="red", width=4),
        ),
        row=2, col=1
    )


    # SWC plot

    fig.add_trace(go.Scatter(
        x=swc.index,
        y=swc,
        mode="lines",
        name="Sliding Window Correlation"
        ), 
        row=3, col=1
    )

    # Highlight center point
    if center + lag < len(swc):
        fig.add_trace(go.Scatter(
            x=[center + lag],
            y=[swc.iloc[center + lag]],
            mode="markers",
            marker=dict(color="red", size=10),
            name="Center Point"
        ), row=3, col=1)

    valid = ~np.isnan(meteo_lagged)
    if valid.sum() > 2:
        corr = np.corrcoef(energy[valid], meteo_lagged[valid])[0, 1]

    return fig, corr

fig, corr = plotly_lagged_correlation(df_merged, lag=lag, window=window, center=center)

st.plotly_chart(fig)
st.write(f"Correlation at lag {lag}: {corr:.3f}")

