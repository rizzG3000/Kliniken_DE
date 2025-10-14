import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
from io import BytesIO

st.set_page_config(page_title="Center Finder", layout="wide")
st.title("🏥 Center Finder – 50 km Radius Map")

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("251013_DE_Augenaerzte_Arzt_Auskunft_Scraped.xlsx")
    df["Full_Address"] = df["Strasse"].astype(str) + ", " + df["PLZ"].astype(str) + " " + df["Stadt"].astype(str)
    return df

df = load_data()

# --- Geolocator Setup ---
geolocator = Nominatim(user_agent="center-finder")

@st.cache_data
def geocode_address(address):
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    return None

@st.cache_data
def geocode_dataframe(df):
    coords = []
    for addr in df["Full_Address"]:
        loc = geolocator.geocode(addr)
        if loc:
            coords.append((loc.latitude, loc.longitude))
        else:
            coords.append((None, None))
    df["Latitude"], df["Longitude"] = zip(*coords)
    return df

# --- Geocode all Centers once ---
if "Latitude" not in df.columns or df["Latitude"].isnull().all():
    st.info("Geocoding centers... (first run may take a few minutes)")
    df = geocode_dataframe(df)

# --- User Input ---
user_address = st.text_input("Enter any address to search around (e.g. Bahnhofstrasse 1, Zürich):")

if user_address:
    user_location = geocode_address(user_address)
    if not user_location:
        st.error("Address could not be found. Please try again.")
    else:
        radius_km = 50
        df["Distance_km"] = df.apply(
            lambda row: geodesic(user_location, (row["Latitude"], row["Longitude"])).km
            if pd.notnull(row["Latitude"]) else None,
            axis=1
        )

        filtered_df = df[df["Distance_km"] <= radius_km].copy()
        st.success(f"{len(filtered_df)} centers found within {radius_km} km of your address.")

        # --- Map ---
        m = folium.Map(location=user_location, zoom_start=9)
        folium.Marker(user_location, popup="Your Address", icon=folium.Icon(color="red")).add_to(m)

        for _, row in filtered_df.iterrows():
            popup_info = f"""
            <b>{row['Name']}</b><br>
            Bereich: {row['Bereich']}<br>
            Zentrum: {row['Zentrum']}<br>
            Adresse: {row['Strasse']}, {row['PLZ']} {row['Stadt']}
            """
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=popup_info,
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)

        st_folium(m, width=900, height=600)

        # --- Download Excel ---
        output = BytesIO()
        filtered_df[
            ["Name", "Bereich", "Zentrum", "Strasse", "PLZ", "Stadt", "Distance_km"]
        ].to_excel(output, index=False)
        st.download_button(
            label="📥 Download Filtered Centers (Excel)",
            data=output.getvalue(),
            file_name="Filtered_Centers.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
