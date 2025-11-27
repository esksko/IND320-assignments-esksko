import streamlit as st

st.title("IND320 Assignments")

# Sidebar title for naviagtion
# Actual sidebar is handled by Streamlit and the "pages" folder
st.sidebar.title("Navigation")

# Setting browser tab title
st.set_page_config(page_title="Weather Dashboard", layout="wide", initial_sidebar_state="expanded")


# Define your pages with groups
MongoDB = st.Page("pages_custom/2_MongoDB.py", title="MongoDB Integration", icon="🗄️")
NewA = st.Page("pages_custom/3_NewA.py", title="STL and Spectrogram", icon="📊")
Table = st.Page("pages_custom/4_Table.py", title="Data Table", icon="📋")
Plot = st.Page("pages_custom/5_Plot.py", title="Weather Plot", icon="🌤️")
NewB = st.Page("pages_custom/6_NewB.py", title="New Page B", icon="📈")
Map = st.Page("pages_custom/7_Map.py", title="Weather Map", icon="🗺️")
Snow_Drift = st.Page("pages_custom/8_Snow_drift.py", title="Snow Drift Analysis", icon="❄️")
Sliding_Window_Correlation = st.Page("pages_custom/9_Sliding_window_correlation.py", title="Sliding Window Correlation", icon="🔄")
Forecasting = st.Page("pages_custom/10_Forecasting.py", title="Weather Forecasting", icon="🌦️")



# Create navigation with sections using a dictionary
pages = {
    "Weather": [Table, Plot, NewB, Snow_Drift],
    "Energy": [MongoDB, NewA, Map, Sliding_Window_Correlation, Forecasting]
}

pg = st.navigation(pages)
pg.run()
