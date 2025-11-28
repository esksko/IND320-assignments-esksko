# pages/6_NewB.py
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor
import requests
import pandas as pd
import tomllib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

st.set_page_config(page_title="Outlier Analysis", layout="wide")

st.title("New Page B: Outlier/SPC analysis and Anomaly/LOF analysis")


# Restore selected price area
selected_area = st.session_state.get("selected_area", "NO1")

# Map price areas to coordinates
area_coords = {
    "NO1": (59.91, 10.75),
    "NO2": (58.15, 7.99),
    "NO3": (63.43, 10.39),
    "NO4": (69.65, 18.96),
    "NO5": (60.39, 5.32)
}

lat, lon = area_coords[selected_area]
selected_year = 2021

tab1, tab2 = st.tabs(["Outlier/SPC Analysis", "Anomaly/LOF Analysis"])



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

def dct_highpass_filter(signal, freq_cutoff):
    coeffs = dct(signal, norm="ortho")
    filtered = np.copy(coeffs)
    filtered[:freq_cutoff] = 0
    return idct(filtered, norm="ortho")



def plot_spc_temperature(time, temperature, freq_cutoff=100, num_std=3):
    """Plot SPC outlier detection with Plotly (clean modern style)."""

    # High-pass filtered DCT
    satv = dct_highpass_filter(temperature, freq_cutoff)

    # Robust stats
    med = np.median(satv)
    mad = np.median(np.abs(satv - med))
    robust_std = mad * 1.4826

    upper_bound = med + num_std * robust_std
    lower_bound = med - num_std * robust_std

    # Build SPC adjustment curves
    upper_curve = temperature + (upper_bound - satv)
    lower_curve = temperature + (lower_bound - satv)

    # Detect outliers
    mask = (satv > upper_bound) | (satv < lower_bound)

    fig = go.Figure()

    # Temperature line
    fig.add_trace(go.Scatter(
        x=time, y=temperature,
        mode="lines",
        name="Temperature",
        line=dict(color="#1f77b4", width=1),
        opacity=0.8
    ))

    # SPC lines
    fig.add_trace(go.Scatter(
        x=time, y=upper_curve,
        mode="lines",
        name="Upper SPC",
        line=dict(color="orange", width=1, dash="3,2")
    ))
    fig.add_trace(go.Scatter(
        x=time, y=lower_curve,
        mode="lines",
        name="Lower SPC",
        line=dict(color="orange", width=1, dash="3,2")
    ))

    # Outlier markers
    fig.add_trace(go.Scatter(
        x=time[mask], y=temperature[mask],
        mode="markers",
        name="Outliers",
        marker=dict(color="red", size=5)
    ))

    fig.update_layout(
        title="Temperature Outliers via Robust SPC",
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        height=450,
        legend=dict(orientation="h", y=-0.2)
    )

    summary = {
        "num_outliers": int(mask.sum()),
        "robust_std": robust_std,
        "outlier_times": time[mask],
        "outlier_values": temperature[mask]
    }
    return fig, summary



def plot_lof(time, values, contamination=0.01, n_neighbors=20, variable_label="Value"):
    """Plot LOF anomalies (Plotly, modern style)."""

    X = np.array(values).reshape(-1, 1)
    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors, contamination=contamination
    )
    labels = lof.fit_predict(X)
    scores = -lof.negative_outlier_factor_

    mask = labels == -1  # LOF marks outliers as -1

    fig = go.Figure()

    # Main line
    fig.add_trace(go.Scatter(
        x=time, y=values,
        mode="lines",
        name=variable_label,
        line=dict(color="#1f77b4", width=1.4)
    ))

    # Outliers
    fig.add_trace(go.Scatter(
        x=time[mask], y=values[mask],
        mode="markers",
        name="Outliers",
        marker=dict(color="red", size=5)
    ))

    fig.update_layout(
        title=f"LOF Anomaly Detection for {variable_label}",
        xaxis_title="Time",
        yaxis_title=variable_label,
        height=450,
        legend=dict(orientation="h", y=-0.2)
    )

    summary = {
        "num_outliers": int(mask.sum()),
        "outlier_times": time[mask],
        "outlier_values": values[mask],
        "lof_scores": scores[mask]
    }

    return fig, summary




# Load Data

if "weather_data" in st.session_state:
    data = st.session_state["weather_data"]
    st.caption("Using cached weather data.")
else:
    data = load_data_from_api(lat, lon, selected_year)
    st.session_state["weather_data"] = data
    st.caption("Loaded fresh weather data.")



# OUTLIER SPC TAB

with tab1:
    st.header("Outlier / SPC Analysis")

    freq_cutoff = st.slider("DCT High-Pass Filter Cutoff", 1, 500, 100)
    num_std = st.slider("SPC Standard Deviations", 1, 5, 3)

    fig, summary = plot_spc_temperature(
        data["time"].values,
        data["temperature_2m"].values,
        freq_cutoff=freq_cutoff,
        num_std=num_std
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary")
    st.write(f"**Detected outliers:** {summary['num_outliers']}")
    st.write(f"**Robust STD:** {summary['robust_std']:.2f}")



# LOF ANOMALY TAB

with tab2:
    st.header("Anomaly / LOF Analysis")

    variable = st.radio(
        "Select Variable",
        ["precipitation", "wind_speed_10m", "wind_gusts_10m"]
    )

    contamination = st.slider("Contamination Level", 0.001, 0.1, 0.01)
    n_neighbors = st.slider("LOF Neighbors", 5, 50, 20)

    fig, summary = plot_lof(
        data["time"].values,
        data[variable].values,
        contamination=contamination,
        n_neighbors=n_neighbors,
        variable_label=variable
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary")
    st.write(f"**Detected anomalies:** {summary['num_outliers']}")
