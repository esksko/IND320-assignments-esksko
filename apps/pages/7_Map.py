import streamlit as st
import plotly.express as px
import json
import os


st.set_page_config(page_title="Map and selectors", layout="wide", initial_sidebar_state="expanded")

st.title("Map and selectors")
st.sidebar.title("Navigation")

with open("data/file.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)


df = 

