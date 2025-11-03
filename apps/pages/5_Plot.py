import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


def plot_all(data, start, end):
    # Group by month number with custom aggregation
    monthly_data = (
        data.groupby(data["time"].dt.month)
        .agg({
            "precipitation (mm)": "sum",            # sum over month
            "wind_speed_10m (m/s)": "mean",         # average
            "wind_gusts_10m (m/s)": "mean",         # average
            "temperature_2m (°C)": "mean",          # average
            "wind_direction_10m (°)": "mean"        # average
        })
        .reset_index(names="month_num")
    )

    # Add month names
    monthly_data["month"] = monthly_data["month_num"].apply(
        lambda m: pd.to_datetime(str(m), format="%m").strftime("%b")
    )

    # Filter months
    monthly_data = monthly_data[
        (monthly_data["month_num"] >= start) & (monthly_data["month_num"] <= end)
    ]

    # Dynamic month labels
    month_labels = monthly_data["month"].tolist()

    # X positions
    x = np.arange(len(month_labels))
    bar_width = 0.3

    # Plot setup
    fig, (ax1_precip, ax2) = plt.subplots(1, 2, figsize=(24, 8), gridspec_kw={"width_ratios": [3, 1]})
    ax1_wind = ax1_precip.twinx()
    ax1_temp = ax1_precip.twinx()

    ax1_precip.set_ylabel("Precipitation (mm)")
    ax1_wind.set_ylabel("Wind Speed (m/s)")
    ax1_temp.set_ylabel("Temperature (°C)", color="red", labelpad=40)
    ax1_temp.tick_params(axis="y", labelcolor="red", direction="in", pad=-30)

    # Plots
    ax1_precip.bar(x - bar_width, monthly_data["precipitation (mm)"], width=bar_width, color="#01386a", label="Precipitation (mm)")
    ax1_wind.bar(x, monthly_data["wind_gusts_10m (m/s)"], width=bar_width, color="#7af9ab", label="Wind Gusts (m/s)")
    ax1_wind.bar(x + bar_width, monthly_data["wind_speed_10m (m/s)"], width=bar_width, color="#75bbfd", label="Wind Speed (m/s)")
    ax1_temp.plot(x, monthly_data["temperature_2m (°C)"], color="red", marker="o", label="Temperature (°C)")

    # Formatting
    ax1_precip.set_xlabel("Month")
    ax1_precip.set_title("Monthly Weather Data 2020")
    ax1_precip.grid(True, alpha=0.3)
    ax1_precip.legend(loc="upper left")
    ax1_wind.legend(loc="upper center")
    ax1_temp.legend(loc="upper right")

    ax1_precip.set_xticks(x)
    ax1_precip.set_xticklabels(month_labels)

    # Y-limits (adjusted for sum of precipitation)
    ax1_precip.set_ylim(0, monthly_data["precipitation (mm)"].max() * 1.2)
    ax1_wind.set_ylim(0, 15)
    ax1_temp.set_ylim(-15, 15)

    # Add text above temperatures
    for xi, yi in zip(x, monthly_data["temperature_2m (°C)"]):
        ax1_temp.text(xi, yi + 0.5, f"{yi:.1f} °C", color="red", ha="center", va="bottom", fontsize=9)

    # Wind direction polar plot
    angles = np.deg2rad(data["wind_direction_10m (°)"])
    ax2 = plt.subplot(122, polar=True)
    ax2.hist(angles, bins=36, color="#fe4b03", alpha=0.75)
    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.set_title("Wind Direction Distribution 2020")
    ax2.set_xlabel("Wind Direction (°)")




st.set_page_config(
    page_title="Plots",
    layout="wide",          # Makes content span the full width
    initial_sidebar_state="expanded",
)


st.title("Plots")
st.sidebar.title("Navigation")



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

# Plot correctly based on selection
if selected_column == "All":
    plot_all(filtered_data, selected_months[0], selected_months[1])
else:
    plt.title(f"{selected_column} from month {selected_months[0]} to {selected_months[1]}")
    if selected_column == "temperature_2m (°C)":
        sns.scatterplot(data=filtered_data, x="time", y="temperature_2m (°C)", hue="temperature_2m (°C)", palette="flare", legend=None, alpha=1, label="Hourly Temperature", s=8)
        plt.xlabel("Date")
        plt.ylabel("Temperature (°C)")
        plt.grid(alpha=0.3)
    elif selected_column == "precipitation (mm)":
        # Plotting monthly precipitation as bars
        monthly_precip = filtered_data.resample("ME", on="time").sum().reset_index()
        sns.barplot(data=monthly_precip, x="time", y="precipitation (mm)", color="#01386a", label="Monthly Precipitation")
        plt.xlabel("Date")
        plt.ylabel("Precipitation (mm)")
    elif selected_column == "wind_speed_10m (m/s)":
        monthly_wind_speed = filtered_data.resample("ME", on="time").mean().reset_index()
        sns.barplot(data=monthly_wind_speed, x="time", y="wind_speed_10m (m/s)", color="#75bbfd")
        plt.xlabel("Date")
        plt.ylabel("Wind Speed (m/s)")
    elif selected_column == "wind_gusts_10m (m/s)":
        monthly_wind_gusts = filtered_data.resample("ME", on="time").mean().reset_index()
        sns.barplot(data=monthly_wind_gusts, x="time", y="wind_gusts_10m (m/s)", color="#7af9ab")
        plt.xlabel("Date")
        plt.ylabel("Wind Gusts (m/s)")
    elif selected_column == "wind_direction_10m (°)":
        angles = np.deg2rad(filtered_data["wind_direction_10m (°)"])
        ax = plt.subplot(111, polar=True)
        ax.hist(angles, bins=36, color="#fe4b03", alpha=0.75)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xlabel("Wind Direction (°)")
    
# Display the plot in Streamlit
st.pyplot(plt)

