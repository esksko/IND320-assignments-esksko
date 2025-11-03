# pages/6_NewB.py
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor
import requests
import pandas as pd

st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")

st.title("New Page B: Outlier/SPC analysis and Anomaly/LOF analysis")


selected_area = st.session_state.get("selected_area", "NO1")

# Map price areas to coordinates
area_coords = {
    "NO1": (59.91, 10.75),  # Oslo
    "NO2": (58.15, 7.99),   # Kristiansand
    "NO3": (63.43, 10.39),  # Trondheim
    "NO4": (69.65, 18.96),  # Tromsø
    "NO5": (60.39, 5.32)    # Bergen
}

lat, lon = area_coords[selected_area]
selected_year = 2021

tab1, tab2 = st.tabs(["Outlier/SPC analysis", "Anomaly/LOF analysis"])


# Data loading function
@st.cache_data(ttl=6000)
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

# Functions for Outlier/SPC and Anomaly/LOF analysis would go here

def dct_highpass_filter(signal, freq_cutoff):
    # Perform DCT
    signal_dct = dct(signal, norm="ortho")


    # Zero out low-frequency components
    filtered_dct = np.copy(signal_dct)
    filtered_dct[:freq_cutoff] = 0

    # Reconstruct high-frequency signal using inverse DCT
    filtered_signal = idct(filtered_dct, norm="ortho")

    return filtered_signal


def detect_temperature_outliers(time, temperature, freq_cutoff=100, num_std=3):
    # Apply high-pass DCT filter
    satv = dct_highpass_filter(temperature, freq_cutoff)

    # Computing robust statistics
    median = np.median(satv)
    mad = np.median(np.abs(satv - median))
    robust_std = mad * 1.4826

    # Defining SPC and control limits
    upper_bound = median + num_std * robust_std
    lower_bound = median - num_std * robust_std

    upper_curve = temperature + (median + num_std * robust_std - satv)
    lower_curve = temperature + (median - num_std * robust_std - satv)

    # Detecting outliers
    outlier_mask = (satv > upper_bound) | (satv < lower_bound)
    outlier_indices = np.where(outlier_mask)[0]

    # Plot temperature and highlight outliers
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(time, temperature, label="Temperature", alpha=0.7)
    #ax.hlines([upper_bound, lower_bound], xmin=time.min(), xmax=time.max(), colors="orange", linestyles="--", label="SPC Boundaries")
    ax.scatter(time[outlier_mask], temperature[outlier_mask],
                color="red", label="Outliers", zorder=5)
    
    plt.plot(time, upper_curve, color='orange', linestyle='--', label='Upper SPC')
    plt.plot(time, lower_curve, color='orange', linestyle='--', label='Lower SPC')
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Temperature Outliers Detected via Robust SPC")
    ax.legend()
    plt.tight_layout()

    # Preparing summary

    summary = {
        "outlier_indices": outlier_indices,
        "outlier_times": time[outlier_mask],
        "outlier_temperatures": temperature[outlier_mask],
        "num_outliers": len(outlier_indices),
        "upper_bound": upper_bound,
        "lower_bound": lower_bound,
        "robust_median": median,
        "robust_std": robust_std
    }

    return fig, summary


def detect_LOF_outliers(time, data_variable, contamination=0.01, n_neighbors=20):
    # Reshaping data for LOF
    X = np.array(data_variable).reshape(-1, 1)

    # LOF
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    pred_labels = lof.fit_predict(X)
    scores = -lof.negative_outlier_factor_ # Higher scores = More anomalous

    # Identifying outliers (LOF labels outliers as -1)
    outlier_mask = pred_labels == -1
    outlier_indices = np.where(outlier_mask)[0]

    # Plot precipitation and highlight outliers
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(time, data_variable, label=selected_variable, alpha=0.7)
    ax.scatter(time[outlier_mask], data_variable[outlier_mask],
                color="red", label="Outliers", zorder=5)
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Value")
    ax.set_title("Anomalies Detected via Local Outlier Factor (LOF)")
    
    ax.legend()
    plt.tight_layout()

    # Summary
    summary = {
        "num_outliers": len(outlier_indices),
        "outlier_indices": outlier_indices,
        "outlier_times": time[outlier_mask],
        "outlier_precipitations": data_variable[outlier_mask],
        "lof_scores": scores[outlier_mask]
    }

    return fig, summary


if "weather_data" in st.session_state:
    data = st.session_state["weather_data"]
    st.write("Using cached weather data.")
else:
    data = load_data_from_api(lat, lon, selected_year, variables=["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"])
    st.session_state["weather_data"] = data
    st.write("Loaded new weather data.")


with tab1:
    st.header("Outlier/SPC Analysis")
    
    selected_variable = "temperature_2m"

    freq_cutoff = st.slider("Frequency Cutoff for DCT High-Pass Filter", min_value=1, max_value=500, value=100, step=1)
    num_std = st.slider("Number of Standard Deviations for SPC Limits", min_value=1, max_value=5, value=3, step=1)

    fig, summary = detect_temperature_outliers(
        data["time"].values,
        data[selected_variable].values,
        freq_cutoff=freq_cutoff,
        num_std=num_std
    )

    st.pyplot(fig)

    st.subheader("Outlier Summary")
    st.write(f"Number of outliers detected: {summary['num_outliers']}")
    st.write(f"Robust standard deviation: {summary['robust_std']:.2f}")



with tab2:
    st.header("Anomaly/LOF Analysis")

    selected_variable = st.radio("Select Variable for LOF Analysis", ["precipitation", "wind_speed_10m", "wind_gusts_10m"])

    contamination = st.slider("Contamination Level", min_value=0.001, max_value=0.1, value=0.01, step=0.001)
    n_neighbors = st.slider("Number of Neighbors for LOF", min_value=5, max_value=50, value=20, step=1)

    fig, summary = detect_LOF_outliers(
        data["time"].values,
        data[selected_variable].values,
        contamination=contamination,
        n_neighbors=n_neighbors
        )
    
    st.pyplot(fig)

    







