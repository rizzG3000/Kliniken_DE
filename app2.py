import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
from io import BytesIO

st.set_page_config(page_title="Center Finder", layout="wide")
st.title("🏥 Sanoptis Add-On Center Finder")

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("251013_DE_Augenaerzte_Arzt_Auskunft_Geocoded.xlsx")
    if not {"Latitude", "Longitude"}.issubset(df.columns):
        st.error("❌ Missing Latitude/Longitude columns. Please upload the geocoded file.")
    df["Full_Address"] = (
        df["Strasse"].astype(str) + ", " + df["PLZ"].astype(str) + " " + df["Stadt"].astype(str)
    )
    return df

df = load_data()

# --- Geolocator ---
geolocator = Nominatim(user_agent="center-finder")

@st.cache_data
def geocode_address(address):
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    return None

# --- Search Inputs ---
st.subheader("🔍 Search Parameters")

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    user_address = st.text_input(
        "Enter an address (e.g. Maximilianstrasse 1, München):",
        key="user_address",
        placeholder="Type an address here..."
    )
with col
