import streamlit as st
import pandas as pd

# Setting browser tab title
st.set_page_config(page_title="Weather Dashboard", layout="wide", initial_sidebar_state="expanded")



# Sidebar title for naviagtion
# Actual sidebar is handled by Streamlit and the "pages" folder
st.sidebar.title("Navigation")

# Define your pages with groups
Homepage = st.Page("pages_custom/Homepage.py", title="Homepage", icon="🏠")
MongoDB = st.Page("pages_custom/2_MongoDB.py", title="MongoDB Integration", icon="🗄️")
NewA = st.Page("pages_custom/3_NewA.py", title="STL and Spectrogram", icon="📊")
Table = st.Page("pages_custom/4_Table.py", title="Data Table", icon="📋")
Plot = st.Page("pages_custom/5_Plot.py", title="Weather Plot", icon="🌤️")
NewB = st.Page("pages_custom/6_NewB.py", title="SPC and LOF Analysis", icon="📈")
Map = st.Page("pages_custom/7_Map.py", title="Weather Map", icon="🗺️")
Snow_Drift = st.Page("pages_custom/8_Snow_drift.py", title="Snow Drift Analysis", icon="❄️")
#Sliding_Window_Correlation = st.Page("pages_custom/9_Sliding_Window_Correlation.py", title="Sliding Window Correlation", icon="🔄")
Forecasting = st.Page("pages_custom/10_Forecasting.py", title="Weather Forecasting", icon="🌦️")


# Create navigation with sections using a dictionary
pages = {
    "Homepage": [Homepage ],
    "Weather": [Table, Plot, NewB, Snow_Drift],
    "Energy": [MongoDB, NewA, Map, Forecasting],
}


pg = st.navigation(pages)
pg.run()


# Only run on the homepage
if pg.title == "Homepage":
    st.title("IND320 - Data to Decision")
    st.markdown(
        """
        ## Welcome to the IND320 Dashboard!

        This dashboard is designed to provide insights into energy production and meteorological data.\n
        Navigate through the different sections using the sidebar to explore various analyses and visualizations.

        ### Sections:
        - **Weather**: Explore weather data tables, plots, and analyses.
        - **Energy**: Dive into MongoDB integration, energy production data, and advanced analyses.

        Enjoy your exploration!
        """
    )   

    # Display an image
    st.image("data/reinebringen.jpg", caption="Reinebringen, Lofoten - Norway", width=1400)





