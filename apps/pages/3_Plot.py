import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


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


# Plotting filtered data
st.write(f"Plot for {selected_column}")
plt.figure(figsize=(16, 6))

if selected_column == "All":
    for col in filtered_data.columns:
        if col != "time":
            sns.lineplot(data=filtered_data, x="time", y=col, label=col)
else:
    sns.lineplot(data=filtered_data, x="time", y=selected_column, color="blue", label=selected_column)


plt.xlabel("Time")
plt.ylabel("Value")
plt.title(f"Weather Data Plot - {selected_column}")
plt.xticks(rotation=45)
plt.legend()
#plt.tight_layout()

st.pyplot(plt)

