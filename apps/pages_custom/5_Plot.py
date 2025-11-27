import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

st.set_page_config(page_title="Plots", layout="wide")

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

    # Aggregate monthly data
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

    month_labels = monthly_data["month"].tolist()
    x = np.arange(len(month_labels))
    bar_width = 0.3

   
    fig = go.Figure()

    # Traces
    # y1 - Precipitation
    fig.add_trace(
        go.Bar(
            x=x - bar_width,
            y=monthly_data["precipitation (mm)"],
            name="Precipitation (mm)",
            marker_color="#01386a",
            width=bar_width  
        )
    )

    # y2 - Wind gusts
    fig.add_trace(
        go.Bar(
            x=x,
            y=monthly_data["wind_gusts_10m (m/s)"],
            name="Wind Gusts (m/s)",
            marker_color="#7af9ab",
            yaxis="y2",
            width=bar_width  
        )
    )

    # y2 - Wind speed 
    fig.add_trace(
        go.Bar(
            x=x + bar_width,
            y=monthly_data["wind_speed_10m (m/s)"],
            name="Wind Speed (m/s)",
            marker_color="#75bbfd",
            yaxis="y2",
            width=bar_width  
        )
    )

    # y3 - Temperature line plot
    fig.add_trace(
        go.Scatter(
            x=x,
            y=monthly_data["temperature_2m (°C)"],
            mode="lines+markers+text",
            text=[f"{t:.1f} °C" for t in monthly_data["temperature_2m (°C)"]],
            textfont=dict(color="red"),
            textposition="top center", 
            marker=dict(color="red", size=8),
            line=dict(color="red", width=2),
            name="Temperature (°C)",
            yaxis="y3"
        )
    )

    # Polar subplot
    fig.add_trace(
        go.Barpolar(
            theta=data["wind_direction_10m (°)"],
            r=np.ones(len(data)),
            marker_color="#fe4b03",
            opacity=0.75,
            name="Wind Direction",
            subplot="polar"
        )
    )

    # Layout
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=x,
            ticktext=month_labels,
            title="Month",
            domain=[0, 0.65]
        ),
        
        # y1 - Precipitation (left)
        yaxis=dict(
            title="Precipitation (mm)",
            range=[0, monthly_data["precipitation (mm)"].max() * 1.2]
        ),

        # y2 - Wind Speed & Gusts (center)
        yaxis2=dict(
            title="Wind Speed (m/s)",
            overlaying="y",
            side="right",
            range=[0, max(monthly_data["wind_gusts_10m (m/s)"].max(), 
                         monthly_data["wind_speed_10m (m/s)"].max()) * 1.2],
            anchor="x"
        ),

        # y3 - Temperature (right)
        yaxis3=dict(
            title=dict(
                text="Temperature (°C)",
                font=dict(color="red")
            ),
            tickfont=dict(color="red"),
            overlaying="y",
            side="right",
            anchor="free",
            position=0.68,
            range=[monthly_data["temperature_2m (°C)"].min() - 2,
                   monthly_data["temperature_2m (°C)"].max() + 5],
            showgrid=False
        ),

        # Polar subplot
        polar=dict(
            domain=dict(x=[0.75, 1.0], y=[0, 1]),
            angularaxis=dict(
                direction="clockwise",
                rotation=90
            )
        ),

        width=1300,
        height=600,
        bargap=0.1,
        legend=dict(x=0.01, y=0.99),
        showlegend=True
    )

    return fig



# Streamlit UI

st.title("Plots")


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
    st.plotly_chart(fig, use_container_width=True)

else:
    # Plotly single-variable hourly line chart
    fig = plot_single_column(selected_column, filtered_data)
    st.plotly_chart(fig, use_container_width=True)
