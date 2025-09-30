import streamlit as st
import pandas as pd

st.title("Table")
st.sidebar.title("Navigation")

@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

# Load data
data = load_data()
st.dataframe(data)

# Filter first month (January)
first_month = data[data["time"].dt.month == 1]

#st.dataframe(first_month)



#Row-wise table: One row per original column (except "time")
#This dataframe has two columns, "variable" and "January Data"
#"variable" contains the original column names (except "time")
#"January Data" contains the corresponding data for January as lists

rowwise_df = pd.DataFrame({
    "variable": [col for col in first_month.columns if col != "time"], 
    "January Data": [first_month[col].values for col in first_month.columns if col != "time"] 
})


# Displays row-wise table with line chart in "January Data" column
st.data_editor(
    rowwise_df,
    column_config={
        "January Data": st.column_config.LineChartColumn(
            label="January 2020",
            width="medium"
        )
    },
    hide_index=True
)