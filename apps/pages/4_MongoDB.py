import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd
import matplotlib.pyplot as plt


st.title("MongoDB integration")
st.sidebar.title("Navigation")
st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")


password = st.secrets["MongoDB"]["pwd"]
cluster = st.secrets["MongoDB"]["cluster"]
database = st.secrets["MongoDB"]["database"]
collection = st.secrets["MongoDB"]["collection"]


uri = f"mongodb+srv://esksko:{password}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority&appName=IND320-esksko"
client = MongoClient(uri, server_api=ServerApi("1"))

# Connecting to the MongoDB database and collection
db = client[database]
col = db[collection]

# Loading all documents from the collection
data = list(col.find())
df = pd.DataFrame(data)

# Dropping the '_id' column if it exists
if "_id" in df.columns:
    df = df.drop(columns=["_id"])


# Splitting page into left and right columns
left_column, right_column = st.columns(2)

with left_column:
    st.subheader("Production Share by Group")

    price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    selected_area = st.radio("Select Price Area", price_areas)

    # Filter data based on selected price area
    area_data = df[df["pricearea"] == selected_area]

    production_by_group = area_data.groupby("productiongroup")["quantitykwh"].sum()

    # Creating pie chart
    plt.figure(figsize=(10, 6))
    plt.pie(production_by_group.values)
    plt.title(f"Production Distribution by Group in {selected_area} (2021)")
    plt.legend(production_by_group.index, title="Production Groups", loc="upper left")

    st.pyplot(plt)


with right_column:
    st.subheader("Monthly Production Trend")

    # Pills for selecting production group
    production_groups = ["hydro", "wind", "solar", "thermal", "other"]
    selected_group = st.pills("Select Production Group", production_groups, selection_mode="multi")

    # Selectbox for selecting month
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    selected_month = st.selectbox("Select Month", months)

    # Filtering data based on selected production group and month
    group_data = df[df["productiongroup"].isin(selected_group)]
    month_data = group_data[group_data["starttime"].dt.month == (months.index(selected_month) + 1)]

    # This creates a pivot table for better plotting
    pivot_data = month_data.pivot_table(values="quantitykwh", index="starttime", columns="productiongroup", aggfunc="sum")

    # Creating line chart
    plt.figure(figsize=(10, 6))
    for column in pivot_data.columns:
        plt.plot(pivot_data.index, pivot_data[column], label=column)
    
    plt.xlabel("Time")
    plt.ylabel("Production (kWh)")
    plt.title(f"Hourly Production by Group  - {selected_month} 2021")
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid()

    st.pyplot(plt)
    
