#!/usr/bin/env python
# coding: utf-8

# In[22]:


import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd  # Assuming you're using pandas to manage your data
import openrouteservice
from openrouteservice import Client
from shapely.geometry import Point
import geopandas as gpd
from folium import GeoJson
import json
from folium.plugins import MarkerCluster
from shapely import wkt
import warnings
from openrouteservice import Client
warnings.filterwarnings('ignore')
import aiohttp
import asyncio
import requests
import nest_asyncio


# In[23]:


st.set_page_config(layout='wide')
st.image('title.png', width=1200)
st.image('logo.png', width=1200)
st.sidebar.write('**demographic variable**')
demo_variable = st.sidebar.selectbox('Select preferred demographic variable', [
        'Population, Total', 'Population, Male', 'Population, Female', 
        'Population, Intersex', 'Sex Ratio (No. of Males per 100 Females)', 
        'Population Density (No. per Sq. Km)', 'Number of Households', 
        'Average Household size', 'Land Area (Sq. Km)', '% of population financially healthy'])
with st.sidebar.form("my_form"):
    # Input fields inside the form
    api_key = st.text_input("Enter your API Key")
    latitude = st.number_input('Enter latitude', value=0.0, format="%.6f")
    longitude = st.number_input('Enter longitude', value=0.0, format="%.6f")
    Branch = st.text_input('Enter branch name')
    isochrone_time = st.number_input('Enter isochrone time in minutes', min_value=1, value=15)
    color = st.selectbox('Select marker color', ['pink', 'blue', 'green', 'orange', 'red', 'darkblue', 'maroon'])
    
    # Submit button inside the form
    add_Location = st.form_submit_button('Add Location')


# In[24]:


@st.cache_data
def read_data():
    stores = pd.read_csv('supermarkets_cordinates.csv')
    county_demographic = pd.read_csv('county_demographics.csv')
    merged_df = pd.merge(stores, county_demographic, on='County', how='left')

    county_df = pd.read_csv('county_geometry_and_demographics.csv')
    county_df['geometry'] = county_df['geometry'].apply(wkt.loads)
    county_gdf = gpd.GeoDataFrame(county_df, geometry='geometry')

    county_store_counts = merged_df.groupby('County')['Branch'].count().reset_index()
    county_store_counts.rename(columns={'Branch': 'Total_number_of_stores'}, inplace=True)
    merged_df = merged_df.merge(county_store_counts, on='County', how='left')

    stores_geometry = [Point(xy) for xy in zip(stores['longitude'], stores['latitude'])]
    stores_gdf = gpd.GeoDataFrame(stores, crs='EPSG:4326', geometry=stores_geometry)

    gdf1 = gpd.read_file('county.shp')
    gdf1 = gdf1.rename(columns={'COUNTY': 'County'})
    complete_gdf = gdf1.merge(merged_df, on='County', how='right')

    if complete_gdf.crs is None:
        complete_gdf.set_crs("EPSG:4326", inplace=True)
    elif complete_gdf.crs.to_string() != 'EPSG:4326':
        complete_gdf = complete_gdf.to_crs("EPSG:4326")

    if county_gdf.crs is None:
        county_gdf.set_crs(epsg=4326, inplace=True)
    elif county_gdf.crs.to_string() != 'EPSG:4326':
        county_gdf = county_gdf.to_crs(epsg=4326)

    return stores_gdf, county_gdf, complete_gdf


# In[25]:


if 'stores_gdf' not in st.session_state or 'county_gdf' not in st.session_state or 'complete_gdf' not in st.session_state:
    stores_data, county_data, complete_data = read_data()
    st.session_state.stores_gdf = stores_data
    st.session_state.county_gdf = county_data
    st.session_state.complete_gdf = complete_data
# Initialize the OpenRouteService client
if not api_key:
    default_key = 'e895c8773e1e452791addb66d57a41e9'
else:
    default_key = api_key
    
@st.cache_data
def updated_gdf():
    stores_data = st.session_state.stores_gdf
    if 'gdf' not in st.session_state:
        color_map = {
            'Naivas': 'orange', 'Quickmart': 'red', 'Carrefour': 'darkblue',
            'Chandarana': 'green', 'Cleanshelf': 'blue', 'Khetias': 'black'
        }
        gdf = gpd.GeoDataFrame(stores_data[['latitude', 'longitude', 'Branch', 'Supermarket_chain']])
        gdf['color'] = gdf['Supermarket_chain'].map(color_map)
        gdf['geometry'] = gpd.points_from_xy(gdf['longitude'], gdf['latitude'])
        gdf.set_crs(epsg=4326, inplace=True)
        st.session_state.gdf = gdf
    return st.session_state.gdf
# Ensure 'gdf' is initialized only once
if 'gdf' not in st.session_state:
    gdf = updated_gdf()
        
def add_markers():
    center_lat = 0.276134723744964
    center_lon = 43.5308662173491
    gdf = st.session_state.gdf
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=5.5)
    for _, location in gdf.iterrows():
        folium.Marker(
            location=[location['latitude'], location['longitude']],
            tooltip=location['Branch'],
            icon=folium.Icon(color=location['color'], icon='info-sign')
        ).add_to(fmap)
    legend_html = '''
    <div style="position: fixed; top: 10px; right: 10px; width: 200px; height: auto; 
                background-color: white; border:2px solid black; z-index:9999; font-size:14px; 
                padding: 10px;">
        <b>Supermarket Chains</b><br>
        <i style="background: orange; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Naivas<br>
        <i style="background: red; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Quickmart<br>
        <i style="background: blue; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Carrefour<br>
        <i style="background: green; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Chandarana<br>
        <i style="background: darkblue; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Cleanshelf<br>
        <i style="background: black; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></i> Khetia's<br>
    </div>
    '''
    # Add legend to the map as a DivIcon
    folium.Marker(
        location= [4.2921, 46.9219],  # Position the legend somewhere on the map (will be hidden by CSS)
        icon=folium.DivIcon(html=legend_html)
    ).add_to(fmap)
    return fmap
    
def create_choropleth():
    county_data = st.session_state.county_gdf
    if not demo_variable or demo_variable not in county_data.columns:
        default_variable = 'Population Density (No. per Sq. Km)'
    else:
        default_variable = demo_variable
        fmap = add_markers()
        folium.Choropleth(
            geo_data=county_data.to_json(),
            name='Choropleth',
            data=county_data,
            columns=['COUNTY', default_variable],
            key_on='feature.properties.COUNTY',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name= default_variable
        ).add_to(fmap)
        # Optional: Add tooltips to show data on hover
        folium.GeoJson(
            county_data,
            tooltip=folium.GeoJsonTooltip(
            fields=['COUNTY', default_variable],
            style=("background-color: white; color: #333333; font-family: Arial; font-size: 12px; padding: 10px;")
            )
        ).add_to(fmap)
        return fmap


# In[26]:


@st.cache_data
def fetch_isochrones(gdf=None, range_minutes=15):
    try:
        if gdf is None:
            gdf = st.session_state.gdf
        isochrones = []  # To store results for all locations
        for _, location in gdf.iterrows():
            url = f"https://api.geoapify.com/v1/isoline"
            params = {
                "lat": location['latitude'],
                "lon": location['longitude'],
                "type": "time",  # Use 'time' for time-based isochrones
                "mode": "drive",  # Default to driving mode
                "range": range_minutes * 60,  # Convert minutes to seconds
                "apiKey": default_key
            }
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise error if the request fails
            iso = response.json()
            if iso and 'features' in iso:  # Check if the response contains isochrone features
                # Create a GeoDataFrame from the GeoJSON isochrone features
                iso_gdf = gpd.GeoDataFrame.from_features(iso['features'], crs='EPSG:4326')
                iso_gdf = iso_gdf.to_crs(epsg=3857)
                # Calculate the area in km²
                iso_gdf['area_km2'] = iso_gdf['geometry'].area / 1e6
                area = iso_gdf['area_km2'].sum()

                # Store isochrone and branch information
                isochrones.append({'iso_gdf': iso_gdf, 'branch': location['Branch']})

        return isochrones  # Return the list of all isochrones
    except requests.RequestException as e:
        st.error(f"Failed to fetch isochrones from Geopify: {e}")
        return None


# In[27]:


def create_isochrones():
    fmap = create_choropleth() 
    isochrones = fetch_isochrones()
    if isochrones:
        for iso_data in isochrones:
            iso_gdf = iso_data['iso_gdf']
            branch = iso_data['branch']
            area = iso_gdf['area_km2'].sum()

            folium.GeoJson(
                iso_gdf.to_crs(epsg=4326),  # Reproject back to EPSG:4326 for display
                name='Isochrones',
                tooltip=folium.Tooltip(f"{branch} Isochrone area, Isochrone size {area:.2f} km²"),
                style_function=lambda x: {'fillColor': 'red', 'color': 'black', 'weight': 1, 'opacity': 0.5}
            ).add_to(fmap)
    return fmap


# In[28]:


def new_isochrone(gdf, range_minutes=15):
    try:
        fmap = create_isochrones()  # Load the existing map
        url = f"https://api.geoapify.com/v1/isoline"

        for _, location in gdf.iterrows():  # Iterate through the new locations
            params = {
                "lat": location['latitude'],
                "lon": location['longitude'],
                "type": "time",  # Use 'time' for time-based isochrones
                "mode": "drive",  # Default to driving mode
                "range": range_minutes * 60,  # Convert minutes to seconds
                "apiKey": default_key
            }
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise error if the request fails
            iso = response.json()

            if iso and 'features' in iso:  # Check if the response contains isochrone features
                # Create a GeoDataFrame from the GeoJSON isochrone features
                iso_gdf = gpd.GeoDataFrame.from_features(iso['features'], crs='EPSG:4326')
                iso_gdf = iso_gdf.to_crs(epsg=3857)
                # Calculate the area in km²
                iso_gdf['area_km2'] = iso_gdf['geometry'].area / 1e6
                area = iso_gdf['area_km2'].sum()

                # Add the location marker and isochrone to the map
                folium.Marker(
                    location=[location['latitude'], location['longitude']],
                    tooltip=location['Branch'],
                    icon=folium.Icon(color=location['color'], icon='info-sign')
                ).add_to(fmap)
                
                folium.GeoJson(
                    iso_gdf.to_crs(epsg=4326),  # Reproject for display
                    name='Isochrones',
                    tooltip=folium.Tooltip(f"{location['Branch']} Isochrone area, Isochrone size {area:.2f} km²"),
                    style_function=lambda x: {'fillColor': 'blue', 'color': 'black', 'weight': 1, 'opacity': 0.5}
                ).add_to(fmap)
        return fmap
    except requests.RequestException as e:
        st.error(f"Failed to fetch new isochrones: {e}")
        return None


# In[31]:


if 'fmap' not in st.session_state:
    st.session_state.fmap = None
    
if 'new_location_gdf' not in st.session_state:
    st.session_state.new_location_gdf = None

if add_Location:
    new_location = {
        'latitude': [latitude],
        'longitude': [longitude],
        'Branch': [Branch],
        'Supermarket_chain': ['New Store'],
        'color': [color],
        'geometry': [Point(longitude, latitude)]
    }
    new_location_gdf = gpd.GeoDataFrame(new_location, geometry='geometry', crs='EPSG:4326')
    st.session_state.new_location_gdf = new_location_gdf  # Store the new location
    fmap = new_isochrone(st.session_state.new_location_gdf, isochrone_time)
    st_folium(fmap, width=1200, height=600)
    st.stop()
else:
    fmap = create_isochrones()
    st_folium(fmap, width=1200, height=600)
    st.stop()


# In[ ]:




