import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd
import plotly.express as px
import tomllib

st.set_page_config(page_title="MongoDB Page", layout="wide", initial_sidebar_state="expanded")

st.title("MongoDB integration")
st.sidebar.title("Navigation")


@st.cache_data(ttl=6000)
def load_mongo_data():
    with open(".streamlit/secrets.toml", "rb") as f:
        cfg = tomllib.load(f)

    PWD = cfg["MongoDB"]["pwd"]

    uri = f"mongodb+srv://esksko:{PWD}@ind320-esksko.5nbj7x0.mongodb.net/?retryWrites=true&w=majority&appName=IND320-esksko"

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["IND320_assignment_4"]
    collection = db["production_data"]

    data = list(collection.find())
    df = pd.DataFrame(data)

    # Convert time column to datetime if needed
    if "starttime" in df.columns:
        df["starttime"] = pd.to_datetime(df["starttime"])

    return df


# Splitting page into left and right columns
left_column, right_column = st.columns(2)


# Initializing session state for selections
if "selected_area" not in st.session_state:
    st.session_state["selected_area"] = "NO1"

if "selected_group" not in st.session_state:
    st.session_state["selected_group"] = ["hydro", "wind", "solar", "thermal", "other"]

# Checking if MongoDB data is loaded
if "mongo_data" not in st.session_state:
    df = load_mongo_data()
    st.session_state["mongo_data"] = df
    st.write("Reading new data")
else:
    df = st.session_state["mongo_data"]
    st.write("Using cached data")


# Dropping the '_id' column if it exists
if "_id" in df.columns:
    df = df.drop(columns=["_id"])



with left_column:
    st.subheader("Production Share by Group")

    price_areas = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    selected_area = st.radio("Select Price Area", 
                             price_areas, 
                             key="area_radio", 
                             index=price_areas.index(st.session_state["selected_area"])
                             )
    
    # Update session state when selection changes
    if selected_area != st.session_state["selected_area"]:
        st.session_state["selected_area"] = selected_area


    # Filter data based on selected price area
    area_data = df[(df["pricearea"] == selected_area) & (df["starttime"].dt.year == 2021)]

    production_by_group = area_data.groupby("productiongroup")["quantitykwh"].sum()

    # Creating pie chart
    fig_pie = px.pie(
        names=production_by_group.index,
        values=production_by_group.values,
        title=f"Production Share by Group in {selected_area} (2021)",
    )

    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)


with right_column:
    st.subheader("Monthly Production Trend")

    # Pills for selecting production group
    production_groups = ["hydro", "wind", "solar", "thermal", "other"]
    selected_group = st.pills("Select Production Group", 
                              production_groups, 
                              key="group_pills", 
                              selection_mode="multi", 
                              default=st.session_state["selected_group"]
                              )
    
    # Update session state when selection changes
    if selected_group != st.session_state["selected_group"]:
        st.session_state["selected_group"] = selected_group

    # Selectbox for selecting month
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    selected_month = st.selectbox("Select Month", months, key="selected_month")

    # Filtering data based on selected production group and month
    #group_data = df[df["productiongroup"].isin(selected_group)]
    filtered_data = df[
        (df["starttime"].dt.year == 2021) &
        (df["starttime"].dt.month == (months.index(selected_month) + 1)) &
        (df["pricearea"] == selected_area) &
        (df["productiongroup"].isin(selected_group))
        ]
   
    # This creates a pivot table for better plotting
    pivot_data = filtered_data.pivot_table(values="quantitykwh", index="starttime", columns="productiongroup", aggfunc="sum")

    # Creating line chart using Plotly

    # Convert pivot table to long format
    plot_df = pivot_data.reset_index().melt(
        id_vars="starttime",
        var_name="productiongroup",
        value_name="quantitykwh"
    )

    fig_line = px.line(
        plot_df,
        x="starttime",
        y="quantitykwh",
        color="productiongroup",
        title=f"Hourly Production by Group in {selected_area} - {selected_month} 2021",
    )

    fig_line.update_layout(
        xaxis_title="Time",
        yaxis_title="Production (kWh)",
        legend_title="Production Group",
    )

    st.plotly_chart(fig_line, use_container_width=True)




with st.expander("Data Source"):
    st.markdown("""
    The data shown on this page comes from **Elhub's Energy Data API** (https://api.elhub.no/), 
    which provides hourly production data for different energy groups across Norwegian price areas.  

    For more details, visit [Elhub API Services](https://api.elhub.no/).
    """)

