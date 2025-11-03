import streamlit as st
from statsmodels.tsa.seasonal import STL
import pandas as pd
import matplotlib.pyplot as plt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import tomllib
from scipy.signal import spectrogram
import numpy as np


st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")

st.title("New Page A: STL and Spectrogram")

if "selected_group" not in st.session_state:
    st.session_state["selected_group"] = ["hydro", "wind", "solar", "thermal", "other"]

if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"


tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram"])

selected_area = st.session_state.get("selected_area", "NO1")
selected_groups = st.session_state.get("selected_group", ["hydro", "wind", "solar", "thermal", "other"])



@st.cache_data(ttl=6000)
def load_mongo_data():
    with open(".streamlit/secrets.toml", "rb") as f:
        cfg = tomllib.load(f)

    PWD = cfg["MongoDB"]["pwd"]

    uri = f"mongodb+srv://esksko:{PWD}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority&appName=IND320-esksko"

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["IND320_assignment_2"]
    collection = db["production_data"]

    data = list(collection.find())
    df = pd.DataFrame(data)

    # Convert time column to datetime if needed
    if "starttime" in df.columns:
        df["starttime"] = pd.to_datetime(df["starttime"])

    return df



# STL and Spectrogram functions
def stl_decomposition(df, price_area="NO1", production_group="Solar", period=24, seasonal=7, trend=169, robust=True):
    data = df[(df["pricearea"] == price_area) & (df["productiongroup"] == production_group)]
    ts = data["quantitykwh"] 
    ts.index = pd.to_datetime(data["starttime"])
    ts.sort_index(inplace=True) # Ensure time series is sorted by datetime

    stl = STL(ts, period=period, seasonal=seasonal, trend=trend, robust=robust)
    result = stl.fit()
    
    # Plot
    fig, ax = plt.subplots(4, 1, figsize=(15, 10), sharex=False)
    ax[0].plot(ts, label='Original')
    ax[0].set_title(f"{production_group} Production ({price_area}) - Original")
    ax[0].legend()

    ax[1].plot(result.trend, label='Trend', color='orange')
    ax[1].set_title("Trend Component")
    ax[1].legend()

    ax[2].plot(result.seasonal, label='Seasonal', color='green')
    ax[2].set_title("Seasonal Component")
    ax[2].legend()

    ax[3].plot(result.resid, label='Residual', color='red')
    ax[3].set_title("Residual Component")
    ax[3].legend()

    plt.tight_layout()

    return fig


def plot_spectrogram(df, price_area="NO1", production_group="Solar", window_length=256, overlap=128):
    data = df[(df["pricearea"] == price_area) & (df["productiongroup"] == production_group)]
    
    ts = data["quantitykwh"]
    ts.index = pd.to_datetime(data["starttime"])
    ts.sort_index(inplace=True)

    # Compute spectrogram
    f, t, Sxx = spectrogram(ts, nperseg=window_length, noverlap=overlap)

    # Map 't' (seconds or indices) to datetime
    # t gives the center of each segment in sample indices, convert to datetime
    start_time = ts.index[0]
    dt = ts.index[1] - ts.index[0]  # assuming uniform spacing
    t_dates = [start_time + i*dt for i in t]

    # Plotting
    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.pcolormesh(t_dates, f, 10 * np.log10(Sxx), shading="gouraud", cmap="viridis")
    ax.set_ylabel("Frequency [1/hour]")
    ax.set_xlabel("Time")
    ax.set_title(f"Spectrogram of {production_group} Production ({price_area})")
    fig.colorbar(im, ax=ax, label="Power [dB]")
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig


elhub_df = load_mongo_data()

with tab1:
    st.header("STL Analysis")

    selected_group_stl = st.radio("Select Production Group for Analysis", st.session_state["selected_group"])

    fig = stl_decomposition(elhub_df, price_area=selected_area, production_group=selected_group_stl)

    st.pyplot(fig)


with tab2:
    st.header("Spectrogram Analysis")

    selected_group_spec = st.radio("Select Production Group for Spectrogram", st.session_state["selected_group"])

    fig = plot_spectrogram(elhub_df, price_area=selected_area, production_group=selected_group_spec)
    
    st.pyplot(fig)
    



