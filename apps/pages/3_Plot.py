import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

st.set_page_config(
    page_title="Weather Data Plots",
    layout="wide",          # Makes content span the full width
    initial_sidebar_state="expanded"
)

"""
On the third page:
A plot of the imported data (see below), including header, axis titles and other relevant formatting.
A drop-down menu (st.selectbox) choosing any single column in the CSV or all columns together.
A selection slider (st.select_slider) to select a subset of the months. Defaults should be the first month.
Data should be read from a local CSV-file (open-meteo-subset.csv, available in the Files here in Canvas), using caching for app speed.
"""


st.title("Plots")


@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df


data = load_data()

columns = ["All"] + [col for col in data.columns if col != "time"]

# Column selection drop-down
selected_column = st.selectbox("Select column to plot", columns)

# Month selection slider
months = [i for i in range(1, 13)]

selected_months = st.select_slider("Select months to display", options=months, value=(1, 1))
st.write(f"Showing: {selected_column} for months {selected_months[0]} to {selected_months[1]}")


# Filtering data for the selected months and columns

if selected_column == "All":
    filtered_data = data[(data["time"].dt.month >= selected_months[0]) & (data["time"].dt.month <= selected_months[1])]
else:
    filtered_data = data[(data["time"].dt.month >= selected_months[0]) & (data["time"].dt.month <= selected_months[1])][["time", selected_column]]

# Group by month instead of day
monthly_precipitation = (data.groupby(data["time"].dt.to_period("M"))["precipitation (mm)"].sum().reset_index())

# Convert back to timestamp for plotting
monthly_precipitation["time"] = monthly_precipitation["time"].dt.to_timestamp()

# Rename for clarity
monthly_precipitation = monthly_precipitation.rename(
    columns={"time": "month", "precipitation (mm)": "total_precipitation"}
)
monthly_precipitation["month"] = monthly_precipitation["month"].dt.strftime("%Y-%m")


# Plotting filtered data
st.write(f"Plot for {selected_column}")
plt.figure(figsize=(16, 6))

if selected_column == "All": 
    all_plots = True
else:
    all_plots = False
    
if all_plots or selected_column == "temperature_2m (°C)":
    sns.scatterplot(data=filtered_data, x="time", y="temperature_2m (°C)", hue="temperature_2m (°C)", palette="flare", legend=None, alpha=1, label="Hourly Temperature", s=8)
if all_plots or selected_column == "precipitation (mm)":
    sns.barplot(data=monthly_precipitation, x="month", y="total_precipitation", color="skyblue_r", hue="total_precipitation")
elif all_plots or selected_column == "wind_speed_10m (m/s)":
    sns.lineplot(data=filtered_data, x="time", y="wind_speed_10m (m/s)", color="blue", label="Daily Average Wind Speed")
elif all_plots or selected_column == "wind_gusts_10m (m/s)":
    sns.lineplot(data=filtered_data, x="time", y="wind_gusts_10m (m/s)", color="orange", label="Hourly Wind Gusts")
elif all_plots or selected_column == "wind_direction_10m (°)":
    angles = np.deg2rad(filtered_data["wind_direction_10m (°)"])
    ax = plt.subplot(111, polar=True)
    ax.hist(angles, bins=36, color="blue", alpha=0.75)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)


plt.xlabel("Time")
plt.ylabel("Value")
plt.title(f"Weather Data Plot - {selected_column}")
plt.xticks(rotation=45)
plt.legend()
#plt.tight_layout()

st.pyplot(plt)

