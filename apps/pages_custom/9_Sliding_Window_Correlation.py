import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import tomllib
from pymongo import MongoClient
from pymongo.server_api import ServerApi


st.set_page_config(page_title="Sliding Window Correlation")

st.title("Sliding-Window Correlation Explorer")

# ---------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------------------
if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"


# ---------------------------------------------------------------------
# LOAD MONGODB DATA
# ---------------------------------------------------------------------
@st.cache_data(ttl=6000)
def load_mongo_data():
    with open(".streamlit/secrets.toml", "rb") as f:
        cfg = tomllib.load(f)

    PWD = cfg["MongoDB"]["pwd"]
    uri = f"mongodb+srv://esksko:{PWD}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority"

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["IND320_assignment_4"]

    # Production and consumption
    df_prod = pd.DataFrame(list(db["production_data"].find()))
    df_cons = pd.DataFrame(list(db["consumption_data"].find()))

    for df in (df_prod, df_cons):
        if "starttime" in df.columns:
            df["starttime"] = pd.to_datetime(df["starttime"])

    return df_prod, df_cons


if "mongo_data" not in st.session_state:
    df_production, df_consumption = load_mongo_data()
    st.session_state["mongo_data"] = df_production, df_consumption
else:
    df_production, df_consumption = st.session_state["mongo_data"]


# ---------------------------------------------------------------------
# LOAD WEATHER BASED ON PRICE AREA
# ---------------------------------------------------------------------
area_coords = {
    "NO1": (59.91, 10.75),
    "NO2": (58.15, 7.99),
    "NO3": (63.43, 10.39),
    "NO4": (69.65, 18.96),
    "NO5": (60.39, 5.32)
}

@st.cache_data(ttl=6000)
def load_weather(lat, lon, year, var):
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={year}-01-01&end_date={year}-12-31"
        f"&hourly={var}&timezone=Europe%2FOslo"
    )

    r = requests.get(url)
    if r.status_code != 200:
        st.error("Failed to load meteorological data")
        return None

    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df.rename(columns={var: "meteo"}, inplace=True)
    return df


# ---------------------------------------------------------------------
# USER CONTROLS
# ---------------------------------------------------------------------
st.subheader("Settings")

c1, c2 = st.columns(2)

with c1:
    selected_year = st.radio("Year", [2021, 2022, 2023, 2024],
                             index=0, horizontal=True)
    
    month_names = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
    }

    selected_month = st.selectbox(
        "Select Month",
        options=list(month_names.keys()),
        format_func=lambda x: month_names[x]
    )



    price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    selected_area = st.radio(
        "Select Price Area",
        price_areas,
        horizontal=True,
        index=price_areas.index(st.session_state["selected_area"],)
    )
    st.session_state["selected_area"] = selected_area

    energy_var = st.radio("Energy Variable",
                          ["production", "consumption"],
                          index=0,
                          horizontal=True)

    met_var = st.selectbox(
        "Meteorological variable:",
        ["temperature_2m", "precipitation", "wind_speed_10m",
         "wind_gusts_10m", "wind_direction_10m"]
    )

with c2:
    window = st.slider("Sliding Window Size (hours)", 24, 720, 168)
    lag = st.slider("Lag (hours)", -168, 168, 0)


# ---------------------------------------------------------------------
# LOAD WEATHER + ENERGY (dynamically based on selected area)
# ---------------------------------------------------------------------
lat, lon = area_coords[selected_area]
df_weather = load_weather(lat, lon, selected_year, met_var)

df_energy_raw = df_production if energy_var == "production" else df_consumption
df_energy = df_energy_raw[
    (df_energy_raw["pricearea"] == selected_area) &
    (df_energy_raw["starttime"].dt.year == selected_year)
]

# Aggregation: some areas have multiple entries per hour
df_energy = df_energy.groupby("starttime")["quantitykwh"].sum().reset_index()
df_energy.rename(columns={"starttime": "time"}, inplace=True)


# ---------------------------------------------------------------------
# MERGE WEATHER + ENERGY
# ---------------------------------------------------------------------
df_merged = pd.merge(
    df_weather[["time", "meteo"]],
    df_energy[["time", "quantitykwh"]],
    on="time",
    how="inner"
)

# Filter month
df_merged = df_merged[df_merged["time"].dt.month == selected_month]
df_merged = df_merged.sort_values("time").reset_index(drop=True)


df_merged = df_merged.sort_values("time").reset_index(drop=True)

# Apply lag
df_merged["meteo_lagged"] = df_merged["meteo"].shift(lag)

max_idx = max(0, len(df_merged) - 1)

center = st.slider(
    "Center Index Highlight",
    0,
    max_idx,
    max_idx // 2 if max_idx > 0 else 0
)


# ---------------------------------------------------------------------
# SLIDING WINDOW CORRELATION PLOT
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# SLIDING WINDOW CORRELATION PLOT (UPDATED)
# ---------------------------------------------------------------------

def plot_swc(df, lag, window, center):
    energy = df["quantitykwh"]
    meteo_lagged = df["meteo_lagged"]

    # Rolling correlation
    swc = energy.rolling(window=window, center=True).corr(meteo_lagged)

    # Calculate correlation in the highlighted window
    w_start = max(0, center - window // 2)
    w_end = min(len(df), center + window // 2)

    if w_end > w_start:
        corr_window = np.corrcoef(
            energy.iloc[w_start:w_end],
            meteo_lagged.iloc[w_start:w_end]
        )[0, 1]
    else:
        corr_window = np.nan

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=False,
        subplot_titles=(
            f"{met_var} (lagged {lag}h)",
            f"{energy_var} (kWh)",
            "Sliding Window Correlation"
        )
    )

    # ------------------------------------------------------
    # 1. Meteorology plot
    # ------------------------------------------------------
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["meteo_lagged"], mode="lines", name="Meteo (lagged)"),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["time"].iloc[w_start:w_end],
            y=df["meteo_lagged"].iloc[w_start:w_end],
            mode="lines",
            line=dict(color="red", width=3),
            name="Window (Meteo)"
        ),
        row=1, col=1
    )

    # ------------------------------------------------------
    # 2. Energy plot
    # ------------------------------------------------------
    fig.add_trace(
        go.Scatter(x=df["time"], y=energy, mode="lines", name="Energy"),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["time"].iloc[w_start:w_end],
            y=energy.iloc[w_start:w_end],
            mode="lines",
            line=dict(color="red", width=3),
            name="Window (Energy)"
        ),
        row=2, col=1
    )

    # ------------------------------------------------------
    # 3. SWC plot
    # ------------------------------------------------------
    fig.add_trace(
        go.Scatter(x=df["time"], y=swc, mode="lines", name="Rolling Corr"),
        row=3, col=1
    )

    # Marker on selected center point
    if not np.isnan(swc.iloc[center]):
        fig.add_trace(
            go.Scatter(
                x=[df["time"].iloc[center]],
                y=[swc.iloc[center]],
                mode="markers",
                marker=dict(color="red", size=10),
                name="Selected Window Corr"
            ),
            row=3, col=1
        )

    fig.update_layout(height=1000, showlegend=False)

    return fig, corr_window


# Generate updated plot
fig, corr_window = plot_swc(df_merged, lag, window, center)

st.plotly_chart(fig, use_container_width=True)

st.info(f"**Correlation in selected window (lag = {lag}h): {corr_window:.3f}**")

