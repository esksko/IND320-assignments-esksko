import streamlit as st


# Setting browser tab title
st.set_page_config(page_title="Weather Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("IND320 Assignments")

# Sidebar title for naviagtion
# Actual sidebar is handled by Streamlit and the "pages" folder
st.sidebar.title("Navigation")

# Define your pages with groups
Homepage = st.Page("pages_custom/Homepage.py", title="Homepage", icon="🏠")
MongoDB = st.Page("pages_custom/2_MongoDB.py", title="MongoDB Integration", icon="🗄️")
NewA = st.Page("pages_custom/3_NewA.py", title="STL and Spectrogram", icon="📊")
Table = st.Page("pages_custom/4_Table.py", title="Data Table", icon="📋")
Plot = st.Page("pages_custom/5_Plot.py", title="Weather Plot", icon="🌤️")
NewB = st.Page("pages_custom/6_NewB.py", title="New Page B", icon="📈")
Map = st.Page("pages_custom/7_Map.py", title="Weather Map", icon="🗺️")
Snow_Drift = st.Page("pages_custom/8_Snow_drift.py", title="Snow Drift Analysis", icon="❄️")
Sliding_Window_Correlation = st.Page("pages_custom/9_Sliding_window_correlation.py", title="Sliding Window Correlation", icon="🔄")
Forecasting = st.Page("pages_custom/10_Forecasting.py", title="Weather Forecasting", icon="🌦️")
Test_1 = st.Page("pages_custom/Test_1.py", title="Test Page 1", icon="🧪")
Test_2 = st.Page("pages_custom/Test_2.py", title="Test Page 2", icon="🧫")


# Create navigation with sections using a dictionary
pages = {
    "Homepage": [Homepage ],
    "Weather": [Table, Plot, NewB, Snow_Drift],
    "Energy": [MongoDB, NewA, Map, Sliding_Window_Correlation, Forecasting],
    "Testing": [Test_1, Test_2]
}

pg = st.navigation(pages)
pg.run()
