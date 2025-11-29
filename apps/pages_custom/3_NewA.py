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

if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"

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


# Checking if MongoDB data is loaded
if "mongo_data" not in st.session_state:
    df_production, df_consumption = load_mongo_data()
    st.session_state["mongo_data"] = df_production, df_consumption
    st.write("Reading new data")
else:
    df_production, df_consumption = st.session_state["mongo_data"]
    st.write("Using cached data")


price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
selected_area = st.radio("Select Price Area", 
                         price_areas,
                         index=price_areas.index(st.session_state["selected_area"]),
                         horizontal=True
                         )
            
st.session_state["selected_area"] = selected_area


production_groups = ["hydro", "wind", "solar", "thermal", "other"]
selected_group = st.radio("Select Production Group for Analysis", 
                              production_groups,
                              horizontal=True)



tab1, tab2 = st.tabs(["STL Analysis", "Spectrogram"])




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


elhub_df, df_consumption = st.session_state["mongo_data"]
elhub_df = elhub_df[elhub_df["starttime"].dt.year == 2021]


with tab1:
    st.header("STL Analysis")
    
    fig = stl_decomposition(elhub_df, price_area=selected_area, production_group=selected_group)

    st.plotly_chart(fig, use_container_width=True)


with tab2:
    st.header("Spectrogram Analysis")

    fig = plot_spectrogram(elhub_df, price_area=selected_area, production_group=selected_group)
    
    st.plotly_chart(fig, use_container_width=True)
    



