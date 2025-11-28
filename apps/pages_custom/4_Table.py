import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")

st.title("Table")



# Initialize session state with defaults if not set
if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"

# Map price areas to coordinates
area_coords = {
    "NO1": (59.91, 10.75),  # Oslo
    "NO2": (58.15, 7.99),   # Kristiansand
    "NO3": (63.43, 10.39),  # Trondheim
    "NO4": (69.65, 18.96),  # Tromsø
    "NO5": (60.39, 5.32)    # Bergen
}

price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
selected_area = st.radio("Select Price Area", 
                         price_areas,
                         index=price_areas.index(st.session_state["selected_area"])
                         )
st.session_state["selected_area"] = selected_area

lat, lon = area_coords[selected_area]
selected_year = 2021

# Caching data to avoid reloading on every interaction
@st.cache_data
def load_data_from_api(lat, lon, year, variables=["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]):
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31&hourly="
    for var in variables:
        url += f"{var}," if var != variables[-1] else f"{var}"
    url += "&timezone=Europe%2FOslo"


    print(f"Downloading data from: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        
        # Extracting hourly data into dataframe
        hourly_data = data.get("hourly", {})
        df = pd.DataFrame(hourly_data)

        # Converting time column to datetime
        df["time"] = pd.to_datetime(df["time"])

        return df

    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return None

    


# Load data
data = load_data_from_api(lat, lon, selected_year, variables=["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"])

# Filter first month (January)
first_month = data[data["time"].dt.month == 1]


# Row-wise table: One row per original column (except "time")
# This dataframe has two columns, "variable" and "January Data"
# "variable" contains the original column names (except "time")
# "January Data" contains the corresponding data for January as lists

rowwise_df = pd.DataFrame({
    "variable": [col for col in first_month.columns if col != "time"], 
    "January Data": [first_month[col].values for col in first_month.columns if col != "time"] 
})


# Displays row-wise table with line chart in "January Data" column
st.data_editor(
    rowwise_df,
    column_config={
        "January Data": st.column_config.LineChartColumn(
            label=f"January {selected_year}",
            width="medium"
        )
    },
    hide_index=True
)
