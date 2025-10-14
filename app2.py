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

# --- Sidebar / Controls ---
st.subheader("🔍 Search Parameters")

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    user_address = st.text_input(
        "Enter an address (e.g. Maximilianstrasse 1, München):",
        key="user_address",
        placeholder="Type an address here..."
    )
with col2:
    radius_km = st.number_input(
        "Radius (km):", min_value=5, max_value=200, value=50, step=5, key="radius"
    )
with col3:
    if st.button("🔎 Search"):
        st.session_state["search_started"] = True

# --- Only show results if a search was triggered ---
if "search_started" in st.session_state and st.session_state["search_started"]:
    if not user_address:
        st.warning("⚠️ Please enter an address before searching.")
    else:
        user_location = geocode_address(user_address)
        if not user_location:
            st.error("❌ Address could not be found. Please try again.")
        else:
            df["Distance_km"] = df.apply(
                lambda row: geodesic(user_location, (row["Latitude"], row["Longitude"])).km
                if pd.notnull(row["Latitude"]) and pd.notnull(row["Longitude"])
                else None,
                axis=1,
            )

            filtered_df = df[df["Distance_km"] <= radius_km].copy()
            st.success(f"✅ {len(filtered_df)} centers found within {radius_km} km of your address.")

            # --- Map ---
            m = folium.Map(location=user_location, zoom_start=9)

            # Draw circle for radius visualization
            folium.Circle(
                location=user_location,
                radius=radius_km * 1000,
                color="red",
                fill=True,
                fill_opacity=0.1
            ).add_to(m)

            folium.Marker(
                user_location, popup="📍 Your Address", icon=folium.Icon(color="red")
            ).add_to(m)

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
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(m)

            st_folium(m, width=900, height=600)

            # --- Download Filtered Excel ---
            output = BytesIO()
            filtered_df[
                ["Name", "Bereich", "Zentrum", "Strasse", "PLZ", "Stadt", "Distance_km"]
            ].to_excel(output, index=False)

            st.download_button(
                label="📥 Download Filtered Centers (Excel)",
                data=output.getvalue(),
                file_name="Filtered_Centers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
