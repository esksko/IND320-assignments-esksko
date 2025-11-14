import streamlit as st
from statsmodels.tsa.seasonal import STL
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import tomllib
from scipy.signal import spectrogram
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")

st.title("New Page A: STL and Spectrogram")


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


if "selected_group" not in st.session_state:
    st.session_state["selected_group"] = ["hydro", "wind", "solar", "thermal", "other"]

if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"

# Checking if MongoDB data is loaded
if "mongo_data" not in st.session_state:
    df = load_mongo_data()
    st.session_state["mongo_data"] = df
    st.write("Reading new data")
else:
    df = st.session_state["mongo_data"]
    st.write("Using cached data")


tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram"])

selected_area = st.session_state.get("selected_area", "NO1")
selected_groups = st.session_state.get("selected_group", ["hydro", "wind", "solar", "thermal", "other"])


# STL and Spectrogram functions
def stl_decomposition(df, price_area="NO1", production_group="Solar",
                      period=24, seasonal=7, trend=169, robust=True):

    data = df[(df["pricearea"] == price_area) &
              (df["productiongroup"] == production_group)]

    ts = data["quantitykwh"]
    ts.index = pd.to_datetime(data["starttime"])
    ts = ts.sort_index()

    stl = STL(ts, period=period, seasonal=seasonal, trend=trend, robust=robust)
    res = stl.fit()

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=["Original", "Trend", "Seasonal", "Residual"]
    )

    fig.add_trace(go.Scatter(x=ts.index, y=ts, name="Original"), row=1, col=1)
    fig.add_trace(go.Scatter(x=ts.index, y=res.trend, name="Trend"), row=2, col=1)
    fig.add_trace(go.Scatter(x=ts.index, y=res.seasonal, name="Seasonal"), row=3, col=1)
    fig.add_trace(go.Scatter(x=ts.index, y=res.resid, name="Residual"), row=4, col=1)

    fig.update_layout(
        height=900,
        showlegend=False,
        title=f"{production_group} Production ({price_area}) – STL Decomposition"
    )

    return fig


def plot_spectrogram(df, price_area="NO1", production_group="Solar",
                     window_length=256, overlap=128):

    data = df[(df["pricearea"] == price_area) &
              (df["productiongroup"] == production_group)]

    ts = data["quantitykwh"].values
    times = pd.to_datetime(data["starttime"]).sort_values()

    f, t, Sxx = spectrogram(ts, nperseg=window_length, noverlap=overlap)

    dt = times.iloc[1] - times.iloc[0]
    t_dates = [times.iloc[0] + i * dt for i in t]

    z_db = 10 * np.log10(Sxx + 1e-12)

    fig = go.Figure(
        data=go.Heatmap(
            x=t_dates,
            y=f,
            z=z_db,
            colorscale="Viridis",
            zmin=np.percentile(z_db, 1),
            zmax=np.percentile(z_db, 99),
            colorbar=dict(title="Power [dB]")

        )
    )

    fig.update_layout(
        title=f"Spectrogram of {production_group} Production ({price_area})",
        xaxis_title="Time",
        yaxis_title="Frequency [1/hour]",
        height=600
    )

    return fig


elhub_df = st.session_state["mongo_data"]

with tab1:
    st.header("STL Analysis")

    selected_group_stl = st.radio("Select Production Group for Analysis", st.session_state["selected_group"])

    fig = stl_decomposition(elhub_df, price_area=selected_area, production_group=selected_group_stl)

    st.plotly_chart(fig, use_container_width=True)


with tab2:
    st.header("Spectrogram Analysis")

    selected_group_spec = st.radio("Select Production Group for Spectrogram", st.session_state["selected_group"])

    fig = plot_spectrogram(elhub_df, price_area=selected_area, production_group=selected_group_spec)
    
    st.plotly_chart(fig, use_container_width=True)
    



