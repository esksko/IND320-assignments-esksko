import streamlit as st
import plotly.express as px
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import tomllib
import pandas as pd


st.set_page_config(page_title="Map and selectors", layout="wide", initial_sidebar_state="expanded")

st.title("Map and selectors")
st.sidebar.title("Navigation")


@st.cache_data(ttl=6000)
def load_mongo_data():
    with open(".streamlit/secrets.toml", "rb") as f:
        cfg = tomllib.load(f)

    PWD = cfg["MongoDB"]["pwd"]

    uri = f"mongodb+srv://esksko:{PWD}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority&appName=IND320-esksko"

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["IND320_assignment_4"]
    collection = db["production_data"]

    data = list(collection.find())
    df = pd.DataFrame(data)

    # Convert time column to datetime if needed
    if "starttime" in df.columns:
        df["starttime"] = pd.to_datetime(df["starttime"])

    return df


with open("data/file.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

    for feature in geojson_data["features"]:
        feature["properties"]["ElSpotOmr"] = feature["properties"]["ElSpotOmr"].replace(" ", "")


# Checking if MongoDB data is loaded
if "mongo_data" not in st.session_state:
    df = load_mongo_data()
    st.session_state["mongo_data"] = df
    st.write("Reading new data")
else:
    df = st.session_state["mongo_data"]
    st.write("Using cached data")


c1, c2 = st.columns([1, 1])

with c1:
    group = st.selectbox("Energy Group", ["hydro", "wind", "solar", "thermal", "other"])

with c2:
    start_date, end_date = st.date_input("Select time interval", value=(df["starttime"].min(), df["starttime"].max()))

selected_area = st.radio("Highlighted Area", ["NO1", "NO2", "NO3", "NO4", "NO5"], index=0, horizontal=True)


df_filtered = df[(df["starttime"] >= pd.to_datetime(start_date)) &
                 (df["starttime"] <= pd.to_datetime(end_date))]

df_area_values = (
    df_filtered.groupby("pricearea")["quantitykwh"]
    .mean()
    .reset_index(name="mean_value")
)

# Plot
fig = px.choropleth_map(df_area_values,
                    geojson=geojson_data,
                    locations="pricearea",
                    featureidkey="properties.ElSpotOmr",
                    color="mean_value",
                    opacity=0.5,
                    color_continuous_scale="Viridis",
                    map_style="open-street-map", 
                    title=f"Average Production Quantity for {group.capitalize()} from {start_date} to {end_date}",
                    center={"lat": 63.4305, "lon": 10.3951},
                    zoom=4
                    )
fig.update_geos(fitbounds="locations", visible=False)

fig
