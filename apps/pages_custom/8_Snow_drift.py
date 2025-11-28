import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import radians
import time
import matplotlib.pyplot as plt


st.set_page_config(page_title="Snow drift")



# Utilities from Snow_drift.py ---------------------------/

def compute_Qupot(hourly_wind_speeds, dt=3600):
    """
    Compute the potential wind-driven snow transport (Qupot) [kg/m]
    by summing hourly contributions using u^3.8.
    
    Formula:
       Qupot = sum((u^3.8) * dt) / 233847
    """
    total = sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847
    return total

def sector_index(direction):
    """
    Given a wind direction in degrees, returns the index (0-15)
    corresponding to a 16-sector division.
    """
    # Center the bin by adding 11.25° then modulo 360 and divide by 22.5°
    return int(((direction + 11.25) % 360) // 22.5)

def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
    """
    Compute the cumulative transport for each of 16 wind sectors.
    
    Parameters:
      hourly_wind_speeds: list of wind speeds [m/s]
      hourly_wind_dirs: list of wind directions [degrees]
      dt: time step in seconds
      
    Returns:
      A list of 16 transport values (kg/m) corresponding to the sectors.
    """
    sectors = [0.0] * 16
    for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
        idx = sector_index(d)
        sectors[idx] += ((u ** 3.8) * dt) / 233847
    return sectors

def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds, dt=3600):
    """
    Compute various components of the snow drifting transport according to Tabler (2003).
    
    Parameters:
      T: Maximum transport distance (m)
      F: Fetch distance (m)
      theta: Relocation coefficient
      Swe: Total snowfall water equivalent (mm)
      hourly_wind_speeds: list of wind speeds [m/s]
      dt: time step in seconds
      
    Returns:
      A dictionary containing:
         Qupot (kg/m): Potential wind-driven transport.
         Qspot (kg/m): Snowfall-limited transport.
         Srwe (mm): Relocated water equivalent.
         Qinf (kg/m): The controlling transport value.
         Qt (kg/m): Mean annual snow transport.
         Control: Process controlling the transport (wind or snowfall).
    """
    Qupot = compute_Qupot(hourly_wind_speeds, dt)
    Qspot = 0.5 * T * Swe  # Snowfall-limited transport [kg/m]
    Srwe = theta * Swe    # Relocated water equivalent [mm]
    
    if Qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall controlled"
    else:
        Qinf = Qupot
        control = "Wind controlled"
    
    Qt = Qinf * (1 - 0.14 ** (F / T))
    
    return {
        "Qupot (kg/m)": Qupot,
        "Qspot (kg/m)": Qspot,
        "Srwe (mm)": Srwe,
        "Qinf (kg/m)": Qinf,
        "Qt (kg/m)": Qt,
        "Control": control
    }


def plot_rose(avg_sector_values, overall_avg):
    """
    Plot a 16-sector wind-rose using Plotly instead of Matplotlib.

    Parameters:
      avg_sector_values: list of 16 transport values (kg/m)
      overall_avg: mean Qt (kg/m)
    """

    # Convert to tonnes / m
    avg_tonnes = np.array(avg_sector_values) / 1000.0

    # Sector directions (16 bins)
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    # Angles centered on each sector bin
    theta = np.linspace(0, 360, 16, endpoint=False)

    # Build Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Barpolar(
        r=avg_tonnes,
        theta=theta,
        width=[360/16]*16,
        marker_line_color="black",
        marker_line_width=1,
        opacity=0.8,
    ))

    overall_tonnes = overall_avg/1000.0

    fig.update_layout(
        title=(
            f"Average Directional Distribution of Snow Transport<br>"
            f"Overall Average Qt: {overall_tonnes:,.1f} tonnes/m"
        ),
        polar=dict(
            angularaxis=dict(
                tickmode="array",
                tickvals=theta,
                ticktext=directions,
                rotation=90, # North at the top
                direction="clockwise"
            )
        ),
        showlegend=False,
        margin=dict(l=30, r=30, t=80, b=30)
    )

    return fig
# --------------------------------------------------------

# Open-Meteo API data 

# Caching data to avoid reloading on every interaction
@st.cache_data
def load_data_from_api(lat, lon, start_date, end_date, variables=["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]):
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly="
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
        st.error(f"API error {response.status_code}")
        return pd.DataFrame()
    

# Streamlit page -----------------------------------------

st.title("Snow drift per season - Tabler (2003)")

if "clicked_coord" not in st.session_state:
    st.warning("No coordinate selected on the map page.\nGo to the map page and click on the map first.")
    st.stop()

lat, lon = st.session_state["clicked_coord"]

st.write(f"Selected coordinates: Latitude {lat:.4f}, Longitude {lon:.4f}")

# Select year range
years=list(range(2021, 2025))
start_year, end_year = st.select_slider(
    "Select year range for analysis:",
    options=years,
    value=(2021, 2024)
)

st.write(f"Selected years: {start_year} to {end_year}")

# Parameters from Snow_drift.py
# Parameters for the snow transport calculation.    
T = 3000      # Maximum transport distance in meters
F = 30000     # Fetch distance in meters
theta = 0.5   # Relocation coefficient

results = []
sector_values = []

for year in range(start_year, end_year+1):
    start_date = f"{year}-07-01"
    end_date = f"{year+1}-06-30"

    df = load_data_from_api(lat, lon, start_date, end_date)

    if df.empty:
        continue
    
    df["Swe_hourly"] = df.apply(
        lambda row: row["precipitation"] if row["temperature_2m"] < 1 else 0,
        axis=1
    )

    Swe_total = df["Swe_hourly"].sum()
    ws = df["wind_speed_10m"].tolist()
    wd = df["wind_direction_10m"].tolist()

    result = compute_snow_transport(T, F, theta, Swe_total, ws)
    Qt = result["Qt (kg/m)"]

    sec = compute_sector_transport(ws, wd)

    results.append({"Season": f"{year}-{year+1}", "Qt (kg/m)": Qt})
    sector_values.append(sec)


# Show results -------------------------------------------

if not results:
    st.error("No snow drift data could be computed for the selected years.")
    st.stop()

df_results = pd.DataFrame(results)

c1, c2 = st.columns(2)

with c1:
    st.subheader("Snow Drift per Season")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_results["Season"],
        y=df_results["Qt (kg/m)"],
        mode="lines+markers",
        name="Qt"
    ))
    fig.update_layout(
        title="Mean Seasonal Snow Drift",
        xaxis_title="Season",
        yaxis_title="Qt (kg/m)"
    )
    st.plotly_chart(fig, use_container_width=True)


with c2:
    # Wind Rose

    avg_sector = np.mean(sector_values, axis=0)
    Qt_avg = df_results["Qt (kg/m)"].mean()

    st.subheader("Wind Rose")

    fig_rose = plot_rose(avg_sector, Qt_avg)
    st.plotly_chart(fig_rose, use_container_width=True)




