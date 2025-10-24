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
    df = pd.read_excel("251024_Aggregated_Centers_Final_v2.xlsx")
    if not {"Latitude", "Longitude"}.issubset(df.columns):
        st.error("❌ Missing Latitude/Longitude columns. Please upload the fully geocoded file.")
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

col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
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
    show_circle = st.toggle("Show Radius Circle", value=True, key="show_circle")
with col4:
    if st.button("🔎 Search"):
        st.session_state["search_started"] = True
with col5:
    if st.button("🔄 Reset Search"):
        for key in ["search_started", "user_address", "radius", "show_circle"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()


# --- Run Search ---
if "search_started" in st.session_state and st.session_state["search_started"]:
    if not user_address:
        st.warning("⚠️ Please enter an address before searching.")
    else:
        user_location = geocode_address(user_address)
        if not user_location:
            st.error("❌ Address could not be found. Please try again.")
        else:
            # Compute distance to each center
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

            # Optional radius circle
            if show_circle:
                folium.Circle(
                    location=user_location,
                    radius=radius_km * 1000,
                    color="red",
                    fill=True,
                    fill_opacity=0.1
                ).add_to(m)

            # Marker for user location
            folium.Marker(
                user_location, popup="📍 Your Address", icon=folium.Icon(color="red")
            ).add_to(m)

            # --- Markers for centers ---
            for _, row in filtered_df.iterrows():
                # Format number of doctors as clean integer or "N/A"
                if pd.notnull(row["num_doctors"]) and str(row["num_doctors"]).strip().lower() != "n/a":
                    try:
                        num_docs_display = str(int(float(row["num_doctors"])))
                    except:
                        num_docs_display = str(row["num_doctors"])
                else:
                    num_docs_display = "N/A"

                popup_info = f"""
                <div style="
                    font-family: Arial, sans-serif;
                    font-size: 13px;
                    line-height: 1.4;
                    padding: 6px 6px 6px 6px;
                    border-radius: 8px;
                    background-color: white;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                    width: 230px;
                ">
                    <strong style="font-size:14px; color:#1E3A8A;">{row['center_name']}</strong><br>
                    <b>Nr. of Doctors:</b> <span style="color:#444;">{num_docs_display}</span><br>
                    <b>Adresse:</b> <span style="color:#444;">{row['Strasse']}, {row['PLZ']} {row['Stadt']}</span><br>
                    <b>Entfernung:</b> <span style="color:#444;">{row['Distance_km']:.1f} km</span>
                </div>
                """
                folium.Marker(
                    location=[row["Latitude"], row["Longitude"]],
                    popup=popup_info,
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(m)

            # Auto-zoom to fit all results
            if not filtered_df.empty:
                bounds = [
                    [filtered_df["Latitude"].min(), filtered_df["Longitude"].min()],
                    [filtered_df["Latitude"].max(), filtered_df["Longitude"].max()],
                ]
                m.fit_bounds(bounds, padding=(30, 30))

            # Display map
            st_folium(
                m,
                width=900,
                height=600,
                key="map",
                use_container_width=True,
                returned_objects=[],  # prevents overlay issue
            )

            # --- Download Filtered Excel ---
            output = BytesIO()
            filtered_df[
                ["center_name", "Type", "num_doctors", "Strasse", "PLZ", "Stadt", "Distance_km"]
            ].to_excel(output, index=False)

            st.download_button(
                label="📥 Download Filtered Centers (Excel)",
                data=output.getvalue(),
                file_name="Filtered_Centers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
