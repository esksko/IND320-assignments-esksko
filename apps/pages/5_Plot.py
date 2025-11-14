import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# Load weather dataset
@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

data = load_data()



# Plot hourly line charts with Plotly
def plot_single_column(column, df):

    # Temperature
    if column == "temperature_2m (°C)":
        fig = go.Figure(go.Scatter(
            x=df["time"],
            y=df[column],
            mode="lines",
            line=dict(color="red"),
            connectgaps=True,
        ))
        fig.update_layout(
            title="Hourly Temperature",
            yaxis_title="Temperature (°C)",
            xaxis_title="Time",
        )
        return fig

    # Precipitation 
    if column == "precipitation (mm)":
        fig = go.Figure(go.Scatter(
            x=df["time"],
            y=df[column],
            mode="lines",
            line=dict(color="#01386a"),
            connectgaps=True,
        ))
        fig.update_layout(
            title="Hourly Precipitation",
            yaxis_title="Precipitation (mm)",
            xaxis_title="Time",
        )
        return fig

    # Wind Speed
    if column == "wind_speed_10m (m/s)":
        fig = go.Figure(go.Scatter(
            x=df["time"],
            y=df[column],
            mode="lines",
            line=dict(color="#75bbfd"),
            connectgaps=True,
        ))
        fig.update_layout(
            title="Hourly Wind Speed (10m)",
            yaxis_title="Wind Speed (m/s)",
            xaxis_title="Time",
        )
        return fig

    # Wind Gusts
    if column == "wind_gusts_10m (m/s)":
        fig = go.Figure(go.Scatter(
            x=df["time"],
            y=df[column],
            mode="lines",
            line=dict(color="#7af9ab"),
            connectgaps=True,
        ))
        fig.update_layout(
            title="Hourly Wind Gusts (10m)",
            yaxis_title="Wind Gusts (m/s)",
            xaxis_title="Time",
        )
        return fig

    # Wind direction (Polar histogram)
    if column == "wind_direction_10m (°)":
        # Convert degrees to radians
        fig = go.Figure(go.Barpolar(
            theta=df[column],
            r=np.ones(len(df)),
            marker_color="#fe4b03",
            opacity=0.75
        ))
        fig.update_layout(
            title="Wind Direction Distribution",
            polar=dict(
                angularaxis=dict(
                    direction="clockwise",
                    rotation=90
                )
            )
        )
        return fig

    return go.Figure()



# Plot all variables together
def plot_all(data, start, end):
    import matplotlib.pyplot as plt

    monthly_data = (
        data.groupby(data["time"].dt.month)
        .agg({
            "precipitation (mm)": "sum",
            "wind_speed_10m (m/s)": "mean",
            "wind_gusts_10m (m/s)": "mean",
            "temperature_2m (°C)": "mean",
            "wind_direction_10m (°)": "mean"
        })
        .reset_index(names="month_num")
    )

    monthly_data["month"] = monthly_data["month_num"].apply(
        lambda m: pd.to_datetime(str(m), format="%m").strftime("%b")
    )

    monthly_data = monthly_data[
        (monthly_data["month_num"] >= start) & (monthly_data["month_num"] <= end)
    ]

    x = np.arange(len(monthly_data["month"]))
    bar_width = 0.3

    fig, (ax1_precip, ax2) = plt.subplots(1, 2, figsize=(24, 8),
                                          gridspec_kw={"width_ratios": [3, 1]})

    ax1_wind = ax1_precip.twinx()
    ax1_temp = ax1_precip.twinx()

    ax1_precip.bar(x - bar_width,
                   monthly_data["precipitation (mm)"], width=bar_width,
                   color="#01386a", label="Precipitation")

    ax1_wind.bar(x,
                 monthly_data["wind_gusts_10m (m/s)"], width=bar_width,
                 color="#7af9ab", label="Wind Gusts")

    ax1_wind.bar(x + bar_width,
                 monthly_data["wind_speed_10m (m/s)"], width=bar_width,
                 color="#75bbfd", label="Wind Speed")

    ax1_temp.plot(x, monthly_data["temperature_2m (°C)"],
                  color="red", marker="o", label="Temperature")

    ax1_precip.set_xticks(x)
    ax1_precip.set_xticklabels(monthly_data["month"])

    angles = np.deg2rad(data["wind_direction_10m (°)"])
    ax2 = plt.subplot(122, polar=True)
    ax2.hist(angles, bins=36, color="#fe4b03", alpha=0.75)

    return fig



# Streamlit UI

st.set_page_config(page_title="Plots", layout="wide")

st.title("Plots")
st.sidebar.title("Navigation")

columns = ["All"] + [col for col in data.columns if col != "time"]

selected_column = st.selectbox("Select column to plot", columns)

months = list(range(1, 13))
selected_months = st.select_slider("Select months", options=months, value=(1, 1))

filtered_data = data[
    (data["time"].dt.month >= selected_months[0]) &
    (data["time"].dt.month <= selected_months[1])
]

# Display plots
if selected_column == "All":
    # Keep original matplotlib multi-plot for "All"
    fig = plot_all(filtered_data, selected_months[0], selected_months[1])
    st.pyplot(fig)

else:
    # Plotly single-variable hourly line chart
    fig = plot_single_column(selected_column, filtered_data)
    st.plotly_chart(fig, use_container_width=True)
