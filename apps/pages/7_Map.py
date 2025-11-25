import streamlit as st
import plotly.express as px
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import tomllib
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests


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



with open("data/file.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

    for feature in geojson_data["features"]:
        feature["properties"]["ElSpotOmr"] = feature["properties"]["ElSpotOmr"].replace(" ", "")


# Checking if MongoDB data is loaded
if "mongo_data" not in st.session_state:
    df_production, df_consumption = load_mongo_data()
    st.session_state["mongo_data"] = df_production, df_consumption
    st.write("Reading new data")
else:
    df_production, df_consumption = st.session_state["mongo_data"]
    st.write("Using cached data")


c1, c2 = st.columns([1, 1])

with c1:
    group = st.selectbox("Energy Group", ["hydro", "wind", "solar", "thermal", "other"])

with c2:
    start_date, end_date = st.date_input("Select time interval", value=(df_consumption["starttime"].min(), df_consumption["starttime"].max()))

c3, c4 = st.columns([1, 1])

with c3:
    selected_area = st.radio("Highlighted Area", ["NO1", "NO2", "NO3", "NO4", "NO5"], index=0, horizontal=True)

with c4:
    selected_group = st.radio("Choose Production or Consumption group", ["Production", "Consumption"], index=0, horizontal=True)

if selected_group == "Production":
    df_filtered = df_production[(df_production["starttime"] >= pd.to_datetime(start_date)) &
                    (df_production["starttime"] <= pd.to_datetime(end_date))]
    
elif selected_group == "Consumption":
    df_filtered = df_consumption[(df_consumption["starttime"] >= pd.to_datetime(start_date)) &
                                 (df_consumption["starttime"] <= pd.to_datetime(end_date))]

df_area_values = (
    df_filtered.groupby("pricearea")["quantitykwh"]
    .mean()
    .reset_index(name="mean_value")
)

# Center on Norway
m = folium.Map(location=[63.43, 10.39], zoom_start=5, tiles="CartoDB positron")

# Add choropleth shading for mean values
folium.Choropleth(
    geo_data=geojson_data,
    name="choropleth",
    data=df_area_values,
    columns=["pricearea", "mean_value"],
    key_on="feature.properties.ElSpotOmr",
    fill_color="YlGnBu",
    fill_opacity=0.6,
    line_opacity=0.5,
    legend_name="Mean Value",
).add_to(m)

# Highlight selected area
folium.GeoJson(
    geojson_data,
    name="highlight",
    style_function=lambda feature: {
        "color": "red" if feature["properties"]["ElSpotOmr"] == selected_area else "black",
        "weight": 4 if feature["properties"]["ElSpotOmr"] == selected_area else 1,
        "fillOpacity": 0,
    },
).add_to(m)

# Enable clicking to drop a pin
m.add_child(folium.LatLngPopup())

# Render map
map_output = st_folium(m, height=600, width=900)

# Show clicked coordinates
if map_output and "last_clicked" in map_output and map_output["last_clicked"]:
    lat = map_output["last_clicked"]["lat"]
    lon = map_output["last_clicked"]["lng"]

    st.session_state["clicked_coord"] = (lat, lon)

    
    # Fetch elevation data
    elev_url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"

    try:
        elev_response = requests.get(elev_url)
        elev_response.raise_for_status()

        if "elevation" in elev_response.json():
            elevation = elev_response.json()["elevation"]
            st.success(f"Clicked at: {lat:.5f}, {lon:.5f}, Elevation: {elevation} meters")
    
    except Exception as e:
        st.error(f"Failed to fetch elevation data: {e}")
