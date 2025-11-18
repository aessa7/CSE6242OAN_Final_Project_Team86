"""
Geo-Equity Index: An Interactive Environmental & Socioeconomic Health Risk Mapping Tool"
A Dash/Plotly web application for GEI scores, mapping CIMC sites with hazard scores etc within a specified radius of an address.

"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt
import os
import geopandas as gpd
from shapely.geometry import Point

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = "Geo-Equity Index: An Interactive Environmental & Socioeconomic Health Risk Mapping Tool"

# Global variables
cimc_data = None
census_tracts_gdf = None  # GeoDataFrame for census tracts
top_features_df = None  # DataFrame for top 10 features by domain
geolocator = Nominatim(user_agent="geoequity_index_dashboard")
hazard_score_min = None
hazard_score_max = None
gei_min = None  # Minimum GEI_overall_score value
gei_max = None  # Maximum GEI_overall_score value
geocode_cache = {}  # Cache for geocoded addresses

def load_cimc_data():
    """Load CIMC data from CSV file"""
    global cimc_data, hazard_score_min, hazard_score_max
    try:
        filename = 'data/CIMC_Sites_Hazard_Score.csv'
        
        if os.path.exists(filename):
            cimc_data = pd.read_csv(filename, low_memory=False)
            print(f"✓ Loaded CIMC data from {filename}: {len(cimc_data)} records")
            
            # Get hazard score range
            if 'Hazard_Score' in cimc_data.columns:
                hazard_score_min = cimc_data['Hazard_Score'].min()
                hazard_score_max = cimc_data['Hazard_Score'].max()
                print(f"✓ Hazard Score range: {hazard_score_min:.2f} to {hazard_score_max:.2f}")
            else:
                print("⚠️  Hazard_Score column not found")
            
            return True
        
        print(f"✗ CIMC_Sites_Hazard_Score.csv not found in current directory")
        return False
        
    except Exception as e:
        print(f"✗ Error loading CIMC data: {e}")
        return False

def load_census_tracts():
    """Load census tract GeoPackage with GEI data"""
    global census_tracts_gdf, gei_min, gei_max
    try:
        filename = 'data/census_tracts_with_gei.gpkg'
        
        if os.path.exists(filename):
            print(f"⏳ Loading census tracts from {filename}...")
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"   File size: {file_size_mb:.2f} MB (this may take a moment)...")
            
            # Load GeoPackage (much faster than GeoJSON)
            census_tracts_gdf = gpd.read_file(filename)
            
            print(f"✓ Loaded census tracts: {len(census_tracts_gdf)} tracts")
            print(f"✓ CRS: {census_tracts_gdf.crs}")
            print(f"✓ Columns: {list(census_tracts_gdf.columns)[:10]}...")  # Show first 10 columns
            
            # Check if CRS conversion is needed
            if census_tracts_gdf.crs and census_tracts_gdf.crs.to_epsg() != 4326:
                print(f"⏳ Converting CRS to EPSG:4326 (this may take a moment)...")
                census_tracts_gdf = census_tracts_gdf.to_crs(epsg=4326)
                print(f"✓ CRS converted to EPSG:4326")
            
            # Get GEI_overall_score range for the full dataset
            if 'GEI_overall_score' in census_tracts_gdf.columns:
                # Exclude -999 values (missing/invalid data)
                valid_gei = census_tracts_gdf[census_tracts_gdf['GEI_overall_score'] != -999]['GEI_overall_score']
                gei_min = valid_gei.min()
                gei_max = valid_gei.max()
                print(f"✓ GEI_overall_score range: {gei_min:.4f} to {gei_max:.4f} (excluding -999 values)")
            else:
                print("⚠️  GEI_overall_score column not found")
            
            return True
        
        print(f"⚠️  census_tracts_with_gei.gpkg not found")
        return False
        
    except Exception as e:
        print(f"✗ Error loading census tracts: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_top_features():
    """Load top 10 features by domain"""
    global top_features_df
    try:
        filename = 'data/GEI_top10_features_2025-11-14.csv'
        
        if os.path.exists(filename):
            top_features_df = pd.read_csv(filename)
            print(f"✓ Loaded top features data: {len(top_features_df)} features")
            return True
        
        print(f"⚠️  GEI_top10_features_2025-11-14.csv not found")
        return False
        
    except Exception as e:
        print(f"✗ Error loading top features: {e}")
        return False

def create_default_us_map():
    """Create a default map showing North America view"""
    # Default view: North America centered
    default_lat = 49.6602
    default_lon = -106.6483
    default_zoom = 1.80
    
    fig = go.Figure()
    
    # Add an invisible trace to initialize the map properly
    fig.add_trace(go.Scattermap(
        lat=[default_lat],
        lon=[default_lon],
        mode='markers',
        marker=dict(size=1, color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=default_lat, lon=default_lon),
            zoom=default_zoom
        ),
        width=1400,  # Fixed width
        height=1000,  # Fixed height
        autosize=False,  # Prevent auto-resizing
        margin=dict(l=0, r=250, t=30, b=0),  # Match the margin for consistency
        hoverdistance=35,  # Easier hover detection (35px radius)
        # title="GEI Dashboard - Enter an address to search"
    )
    
    return fig

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 3956  # Earth radius in miles

def calculate_zoom_for_radius(radius_miles):
    """
    Calculate appropriate zoom level to show 1.5x the search radius
    Formula based on: zoom = log2(world_width / (radius * 2 * 1.5))
    Adjusted for miles and map display
    """
    # Display area should be 1.5x the radius (so 3x radius diameter)
    display_diameter = radius_miles * 3
    
    # Approximate zoom levels for different distances (empirically adjusted)
    # These values ensure the area fits nicely in the viewport
    if display_diameter <= 5:
        return 13
    elif display_diameter <= 10:
        return 12
    elif display_diameter <= 20:
        return 11
    elif display_diameter <= 40:
        return 10
    elif display_diameter <= 80:
        return 9
    elif display_diameter <= 150:
        return 8
    elif display_diameter <= 300:
        return 7
    else:
        return 6

def wrap_text(text, width=40):
    """Insert <br> line breaks to wrap long strings in Plotly hover text.
    Keeps words intact and wraps at approximately `width` characters.
    """
    try:
        if text is None:
            return ""
        s = str(text)
        words = s.split(" ")
        lines = []
        current = ""
        for w in words:
            # +1 for space if current not empty
            if len(current) + (1 if current else 0) + len(w) > width:
                if current:
                    lines.append(current)
                current = w
            else:
                current = f"{current + ' ' if current else ''}{w}"
        if current:
            lines.append(current)
        return "<br>".join(lines)
    except Exception:
        # Fallback: return original text if wrapping fails
        return str(text) if text is not None else ""

def get_coordinates(address):
    """Geocode an address to lat/lon with caching"""
    # Check cache first
    if address in geocode_cache:
        print(f"✓ Using cached coordinates for: {address[:50]}...")
        return geocode_cache[address]
    
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            result = (location.latitude, location.longitude, location.address)
            geocode_cache[address] = result  # Cache the result
            return result
        # No location found - this is a valid address that couldn't be geocoded
        print(f"⚠️  No location found for address: {address}")
        return None, None, "ADDRESS_NOT_FOUND"
    except Exception as e:
        # Distinguish between different error types
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Check for common Nominatim/network errors
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"❌ Geocoding timeout error: {error_msg}")
            return None, None, "TIMEOUT_ERROR"
        elif "too many requests" in error_msg.lower() or "rate limit" in error_msg.lower():
            print(f"❌ Rate limit error: {error_msg}")
            return None, None, "RATE_LIMIT_ERROR"
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            print(f"❌ Network error: {error_msg}")
            return None, None, "NETWORK_ERROR"
        else:
            print(f"❌ Geocoding error ({error_type}): {error_msg}")
            return None, None, "GEOCODING_ERROR"

def get_census_tract_info(lat, lon):
    """Get census tract information for a given latitude/longitude point"""
    global census_tracts_gdf
    
    if census_tracts_gdf is None:
        return None
    
    try:
        # Create a point from the coordinates
        point = Point(lon, lat)
        
        # Find census tracts that contain this point
        containing_tracts = census_tracts_gdf[census_tracts_gdf.geometry.contains(point)]
        
        if len(containing_tracts) > 0:
            # Get the first (should be only one) tract containing the point
            tract = containing_tracts.iloc[0]
            
            # Extract relevant information
            info = {
                'geoid': tract.get('GEOID', 'N/A'),
                'census_tract': tract.get('Census Tract', 'N/A'),
                'gei_overall_score': tract.get('GEI_overall_score', 'N/A'),
                'gei_health_score': tract.get('GEI_health_score', 'N/A'),
                'gei_socio_score': tract.get('GEI_socio_score', 'N/A'),
                'gei_env_score': tract.get('GEI_env_score', 'N/A'),
            }
            
            print(f"✓ Found census tract: GEOID={info['geoid']}, GEI={info['gei_overall_score']}")
            return info
        else:
            print(f"⚠️  No census tract found for point ({lat}, {lon})")
            return None
            
    except Exception as e:
        print(f"Error getting census tract info: {e}")
        import traceback
        traceback.print_exc()
        return None


def filter_cimc_within_radius(center_lat, center_lon, radius_miles):
    """Filter CIMC data within radius"""
    if cimc_data is None:
        return pd.DataFrame()
    
    # Use specific column names for CIMC data
    lat_col = 'LATITUDE'
    lon_col = 'LONGITUDE'
    
    if lat_col not in cimc_data.columns or lon_col not in cimc_data.columns:
        print(f"Could not find {lat_col}/{lon_col} columns in CIMC data")
        print(f"Available columns: {list(cimc_data.columns)}")
        return pd.DataFrame()
    
    # Calculate distances using vectorized operations
    # Filter out rows with missing coordinates
    valid_coords = cimc_data[[lat_col, lon_col]].dropna()
    
    if len(valid_coords) == 0:
        return pd.DataFrame()
    
    # Vectorized distance calculation
    try:
        lats = valid_coords[lat_col].astype(float)
        lons = valid_coords[lon_col].astype(float)
        
        # Calculate distances for all valid coordinates at once
        distances = lats.apply(lambda lat: haversine_distance(center_lat, center_lon, lat, lons.loc[lats[lats == lat].index[0]]))
        
        # More efficient: use list comprehension with zip
        distances = [haversine_distance(center_lat, center_lon, lat, lon) 
                     for lat, lon in zip(lats, lons)]
        
        # Create series with original indices
        distance_series = pd.Series(distances, index=valid_coords.index)
        
        # Filter by radius
        within_radius = distance_series[distance_series <= radius_miles]
        
        if len(within_radius) > 0:
            filtered_df = cimc_data.loc[within_radius.index].copy()
            filtered_df['distance_miles'] = within_radius.values
            return filtered_df.sort_values('distance_miles')
    except (ValueError, TypeError):
        pass
    
    return pd.DataFrame()

def filter_census_tracts_within_radius(center_lat, center_lon, radius_miles):
    """Filter census tracts that intersect with the search radius"""
    global census_tracts_gdf
    
    if census_tracts_gdf is None:
        return None
    
    try:
        # Convert radius from miles to degrees (approximate)
        # 1 degree latitude ≈ 69 miles
        # Add some buffer to ensure we capture tracts at the edge
        radius_degrees = (radius_miles * 1.2) / 69.0  # 20% buffer for edge tracts
        
        # Create a bounding box for filtering
        min_lat = center_lat - radius_degrees
        max_lat = center_lat + radius_degrees
        min_lon = center_lon - radius_degrees
        max_lon = center_lon + radius_degrees
        
        # Filter tracts within expanded bounding box
        filtered_tracts = census_tracts_gdf.cx[min_lon:max_lon, min_lat:max_lat]
        
        return filtered_tracts
        
    except Exception as e:
        print(f"Error filtering census tracts: {e}")
        return None

def create_map_figure(address, radius_miles, zoom_level=None, use_light_basemap='light'):
    """Create the main map figure with optional lightweight basemap"""
    # Calculate appropriate zoom based on radius (to show 1.5x the radius)
    auto_zoom = calculate_zoom_for_radius(radius_miles)
    
    # Use auto zoom if no manual zoom provided, otherwise use manual zoom
    zoom_to_use = zoom_level if zoom_level is not None else auto_zoom
    
    # Get coordinates for the address
    try:
        geocode_result = get_coordinates(address)
        if geocode_result is None or len(geocode_result) != 3:
            print(f"❌ Invalid geocoding result: {geocode_result}")
            lat, lon, error_type = None, None, "UNKNOWN_ERROR"
        else:
            lat, lon, formatted_address_or_error = geocode_result
            
            # Check if we got an error code instead of a formatted address
            if lat is None or lon is None:
                error_type = formatted_address_or_error
                formatted_address = None
            else:
                formatted_address = formatted_address_or_error
                error_type = None
    except Exception as e:
        print(f"❌ Error unpacking geocode result: {e}")
        lat, lon, formatted_address, error_type = None, None, None, "UNPACKING_ERROR"
    
    if lat is None or lon is None:
        # Return empty figure with appropriate error message based on error type
        fig = go.Figure()
        
        # Determine error message based on error type
        if error_type == "ADDRESS_NOT_FOUND":
            error_title = "Address Not Found"
            error_message = f"Could not find coordinates for: {address}\n\nPlease check the address and try again."
        elif error_type == "TIMEOUT_ERROR":
            error_title = "Geocoding Service Timeout"
            error_message = f"The geocoding service timed out.\n\nPlease try again in a moment."
        elif error_type == "RATE_LIMIT_ERROR":
            error_title = "Rate Limit Exceeded"
            error_message = f"Too many requests to the geocoding service.\n\nPlease wait a moment and try again."
        elif error_type == "NETWORK_ERROR":
            error_title = "Network Error"
            error_message = f"Could not connect to the geocoding service.\n\nPlease check your connection and try again."
        elif error_type == "GEOCODING_ERROR":
            error_title = "Geocoding Error"
            error_message = f"An error occurred while geocoding the address.\n\nPlease try a different address format."
        else:
            error_title = "Error"
            error_message = f"An unexpected error occurred.\n\nPlease try again."
        
        fig.add_annotation(
            text=error_message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red"),
            align="center"
        )
        fig.update_layout(
            title=f"Error: {error_title}",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig, f"Error: {error_title}", 0, None, None
    
    # Create base map
    fig = go.Figure()
    
    # Layer 1: Add census tract polygons first (so they appear below other markers)
    nearby_tracts = filter_census_tracts_within_radius(lat, lon, radius_miles)
    if nearby_tracts is not None and len(nearby_tracts) > 0:
        # Convert GeoDataFrame to GeoJSON format for Plotly
        import json
        
        # Use GEI_overall_score column for coloring
        if 'GEI_overall_score' in nearby_tracts.columns:
            # Filter out tracts with -999 values (missing/invalid data)
            valid_tracts = nearby_tracts[nearby_tracts['GEI_overall_score'] != -999].copy()
            
            if len(valid_tracts) > 0:
                # Create choropleth with GEI_overall_score data using blue gradient
                geojson_data = json.loads(valid_tracts.to_json())
                
                # Add choropleth layer with blue color scale
                fig.add_trace(go.Choroplethmap(
                    geojson=geojson_data,
                    locations=valid_tracts.index,
                    z=valid_tracts['GEI_overall_score'],
                    colorscale='RdYlGn',  #'Blues',  # Light blue to dark blue gradient
                    reversescale=True, 
                    zmin=gei_min,  # Use full range from entire dataset (excluding -999)
                    zmax=gei_max,
                    marker_opacity=0.6,
                    marker_line_width=0.5,
                    marker_line_color='white',
                    colorbar=dict(
                        title="GEI Score",
                        thickness=15,
                        len=0.5,
                        x=1.05,
                        y=0.75  # Align with top of map
                    ),
                    hovertemplate='<b>Census Tract</b><br>' +
                                 'GEI_overall_score: %{z:.4f}<extra></extra>',
                    hoverlabel=dict(namelength=-1),
                    name='Census Tracts'
                ))
        else:
            # No GEI_overall_score data, just show tract boundaries
            geojson_data = json.loads(nearby_tracts.to_json())
            fig.add_trace(go.Choroplethmap(
                geojson=geojson_data,
                locations=nearby_tracts.index,
                z=[1] * len(nearby_tracts),  # Uniform color
                colorscale=[[0, 'lightgray'], [1, 'lightgray']],
                marker_opacity=0.3,
                marker_line_width=0.5,
                marker_line_color='gray',
                showscale=False,
                hovertemplate='<b>Census Tract</b><extra></extra>',
                hoverlabel=dict(namelength=-1),
                name='Census Tracts'
            ))
    
    # Layer 2: Get and add CIMC points (before address marker so address appears on top)
    nearby_cimc = filter_cimc_within_radius(lat, lon, radius_miles)
    cimc_count = len(nearby_cimc)
    
    if cimc_count > 0:
        # Prepare CIMC data for plotting
        cimc_lats = []
        cimc_lons = []
        cimc_texts = []
        cimc_hazard_scores = []
        
        # Use specific column names for CIMC data
        lat_col = 'LATITUDE'
        lon_col = 'LONGITUDE'
        
        # Use itertuples() for much faster iteration than iterrows()
        for point in nearby_cimc.itertuples():
            try:
                point_lat = float(getattr(point, lat_col))
                point_lon = float(getattr(point, lon_col))
                
                # Create hover text
                hover_text = f"CIMC Site:"
                
                # Add site name first
                if hasattr(point, 'PRIMARY_NAME') and pd.notna(getattr(point, 'PRIMARY_NAME')):
                    site_name_wrapped = wrap_text(str(getattr(point, 'PRIMARY_NAME')), 38)
                    hover_text += f"<br>Site Name: {site_name_wrapped}"
                
                # Add hazard score if available
                if hasattr(point, 'Hazard_Score') and pd.notna(getattr(point, 'Hazard_Score')):
                    hazard_score = float(getattr(point, 'Hazard_Score'))
                    hover_text += f"<br>Hazard Score: {hazard_score:.2f}"
                    cimc_hazard_scores.append(hazard_score)
                else:
                    cimc_hazard_scores.append(None)
                
               # Add a note telling users to click for more details
                hover_text += f"<br><i>Click for more details</i>"
                
                # # Add URL as a clickable link if available
                # if 'URL' in point and pd.notna(point['URL']):
                #     url = str(point['URL'])
                #     hover_text += f"<br>URL: <a href='{url}' target='_blank' style='color: #3498db;'>Go to URL</a>"
                
                cimc_lats.append(point_lat)
                cimc_lons.append(point_lon)
                cimc_texts.append(hover_text)
                    
            except (ValueError, KeyError):
                continue
        
        # Add CIMC points to map
        if cimc_lats:
            # Create customdata with lat/lon pairs for reliable click detection
            cimc_customdata = [[lat, lon] for lat, lon in zip(cimc_lats, cimc_lons)]
            
            # Underlay outline (slightly larger white circles) to create separation
            fig.add_trace(go.Scattermap(
                lat=cimc_lats,
                lon=cimc_lons,
                mode='markers',
                name='CIMC Outline',
                showlegend=False,
                marker=dict(
                    size=12,  # slightly larger than main points for a thin outline
                    color='black',
                    opacity=1.0,
                    showscale=False
                ),
                customdata=cimc_customdata,
                hoverinfo='skip'
            ))

            # Main colored CIMC points on top
            fig.add_trace(go.Scattermap(
                lat=cimc_lats,
                lon=cimc_lons,
                mode='markers',
                name='CIMC Sites',
                showlegend=False,
                marker=dict(
                    size=10,
                    color=cimc_hazard_scores,
                    colorscale='YlOrRd',  # Yellow to Orange to Red
                    cmin=hazard_score_min,
                    cmax=hazard_score_max,
                    colorbar=dict(
                        title="CIMC Hazard Score",
                        thickness=15,
                        len=0.5,
                        x=1.15,
                        y=0.75  # Align with top of map
                    ),
                    showscale=True
                ),
                customdata=cimc_customdata,
                text=cimc_texts,
                hoverinfo='text'
            ))
    
    # Layer 3: Add search location marker LAST (marker on top of everything)
    print(f"🎯 Adding address marker at: lat={lat}, lon={lon}")  # Debug print
    
    # Get census tract info for the search address
    census_info = get_census_tract_info(lat, lon)
    
    # Build hover text with census tract info
    # Wrap address: break after the first comma only and use a wider line width
    hover_text = f"📍 Search Location<br>{wrap_text(formatted_address.replace(', ', ', <br>', 1), 50)}"
    if census_info:
        hover_text += f"<br><br><b>GEI Score Info:</b>"
        # hover_text += f"<br>GEOID: {census_info['geoid']}"
        hover_text += f"<br>Census Tract: {census_info['census_tract']}"
        if census_info['gei_overall_score'] != 'N/A':
            hover_text += f"<br>GEI Overall Score: {census_info['gei_overall_score']:.4f}"
        else:
            hover_text += f"<br>GEI Overall Score: {census_info['gei_overall_score']}"
    else:
        hover_text += "<br><br>⚠️ Census tract information not available"
    
    # Bullseye effect: Add concentric circles (outer to inner)
    # Outer ring (largest, most transparent)
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(size=45, color='rgba(0,123,255,0.3)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Middle ring
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(size=30, color='rgba(138,43,226,0.5)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Inner ring
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(size=18, color='rgba(255,0,255,0.7)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Center marker with magenta ring (with hover info)
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(size=10, color='#FF00FF'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Center dot (with hover info)
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(size=6, color='#8B00FF'),
        hovertext=[hover_text],
        hoverinfo='text',
        name='Search Address',
        showlegend=False
    ))
    
    # Choose basemap style based on preference
    # Options: "open-street-map" (full detail), "carto-positron" (light), "white-bg" (fastest, no tiles)
    if use_light_basemap == 'none':
        map_style = "white-bg"  # No tiles, just white background (fastest)
    elif use_light_basemap == 'light':
        map_style = "carto-positron"  # Light, fast-loading map
    else:  # 'detailed'
        map_style = "open-street-map"  # Full detail map (slower)
    
    # Update map layout
    fig.update_layout(
        map=dict(
            style=map_style,
            center=dict(lat=lat, lon=lon),
            zoom=zoom_to_use
        ),
        width=1400,  # Fixed width
        height=1000,  # Fixed height
        autosize=False,  # Prevent auto-resizing
        margin=dict(l=0, r=250, t=60, b=0),  # Increased top margin for title spacing
        title=f"Found <b>{len(nearby_cimc)}</b> CIMC sites within <b>{radius_miles}</b> miles of: <br>{formatted_address}",
        hoverlabel=dict(
            bgcolor="white",  # White background
            bordercolor="black",  # Black border
            font=dict(color="black", size=13),  # Black text
            namelength=-1,  # Show full text
            align="left"  # Left align text for better readability
        ),
        hovermode='closest',  # Keep tooltip visible on closest element
        hoverdistance=35  # Easier hover detection (35px radius)
    )
    
    return fig, formatted_address, cimc_count, census_info, nearby_cimc

# Load data on startup
print("="*60)
print("LOADING DATA AT STARTUP")
print("="*60)
data_loaded = load_cimc_data()
census_loaded = load_census_tracts()
top_features_loaded = load_top_features()
print("="*60)

# Define the app layout
app.layout = html.Div([
    # Welcome Modal
    html.Div([
        html.Div([
            html.Div([
                html.H2("Welcome to the Geo-Equity Index", style={'color': '#2c3e50', 'marginBottom': 20}),
                html.P([
                    "Welcome to the Geo-Equity Index—a comprehensive tool that aggregates data from the ",
                    html.Strong("Environmental Protection Agency (EPA)"), ", ",
                    html.Strong("Center for Disease Control (CDC)"), ", the ",
                    html.Strong("U.S. Census Bureau"), 
                    ", and other authoritative sources to generate a singular health score for your neighborhood. ",
                    "The GEI score, rated from ",
                    html.Strong("0 (best) to 1 (worst)"),
                    ", provides an at-a-glance assessment of environmental and socioeconomic health factors in your area."
                ], style={'marginBottom': 15, 'lineHeight': 1.6}),
                html.P([
                    "The tool also incorporates hazardous sites as defined by the EPA's ",
                    html.Strong("Cleanup In My Community (CIMC)"),
                    " program, with each site ranked on a scale of ",
                    html.Strong("0 to 6 (most severe)"),
                    " for hazard severity.",
                    " Simply enter an address, and the interactive map will display a detailed summary of the region along with nearby hazardous sites. Below the map, a comprehensive feature table breaks down your address's score in depth, providing transparency into the underlying health metrics."
                ], style={'marginBottom': 20, 'lineHeight': 1.6}),
                html.Button(
                    'Get Started',
                    id='close-modal',
                    n_clicks=0,
                    style={
                        'backgroundColor': '#3498db',
                        'color': 'white',
                        'padding': '12px 30px',
                        'fontSize': 16,
                        'border': 'none',
                        'borderRadius': 5,
                        'cursor': 'pointer',
                        'width': '100%'
                    }
                )
            ], style={
                'backgroundColor': 'white',
                'padding': 40,
                'borderRadius': 10,
                'maxWidth': 700,
                'margin': '0 auto',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], id='welcome-modal', style={
            'position': 'fixed',
            'top': 0,
            'left': 0,
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0,0,0,0.5)',
            'zIndex': 9999,
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'padding': 20
        })
    ], id='modal-container'),
    
    html.Div([
        # Header with About button
        html.Div([
            html.H1("Geo-Equity Index: \n \
       An Interactive Environmental & Socioeconomic Health Risk Mapping Tool",
                    style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 10, 'display': 'inline-block', 'width': '100%'}),
            html.Div([
                html.Button(
                    'ℹ️ Learn more about GEI',
                    id='about-button',
                    n_clicks=0,
                    style={
                        'backgroundColor': '#95a5a6',
                        'color': 'white',
                        'padding': '8px 20px',
                        'fontSize': 14,
                        'border': 'none',
                        'borderRadius': 5,
                        'cursor': 'pointer'
                    }
                )
            ], style={'textAlign': 'center', 'marginBottom': 20})
        ]),
        
        # Input controls
        html.Div([
            html.Label("Enter Address (USA Only):", style={'fontWeight': 'bold', 'marginBottom': 5}),
            html.Div([
                dcc.Input(
                    id='address-input',
                    type='text',
                    placeholder='Enter street address (e.g., 1600 Pennsylvania Ave NW, Washington, DC)',
                    value='',
                    debounce=True,  # Enable Enter key submission
                    style={'width': '100%', 'padding': 10, 'fontSize': 14}
                ),
                html.Button(
                    'Search',
                    id='search-button',
                    n_clicks=0,
                    style={
                        'backgroundColor': '#3498db',
                        'color': 'white',
                        'padding': '10px 24px',
                        'fontSize': 14,
                        'border': 'none',
                        'borderRadius': 5,
                        'cursor': 'pointer',
                        'marginLeft': 10,
                        'verticalAlign': 'top'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'stretch', 'gap': '10px'})
        ], style={'marginBottom': 20}),
        
        # Map style selector
        html.Div([
            html.Label("Map Style:", style={'fontWeight': 'bold', 'marginRight': 10, 'display': 'inline-block'}),
            dcc.RadioItems(
                id='map-style-toggle',
                options=[
                    {'label': ' No Basemap (Fastest)', 'value': 'none'},
                    {'label': ' Light (Fast)', 'value': 'light'},
                    {'label': ' Detailed (Slowest)', 'value': 'detailed'}
                ],
                value='light',
                inline=True,
                style={'display': 'inline-block'}
            )
        ], style={'textAlign': 'center', 'marginBottom': 20}),
        
        # Status message with loading spinner
        html.Div([
            dcc.Loading(
                id="loading-spinner",
                type="default",  # Options: "graph", "cube", "circle", "dot", "default"
                children=html.Div(id='status-message', style={'display': 'inline-block', 'verticalAlign': 'middle'}),
                color="#3498db",
                parent_style={'display': 'inline-block', 'verticalAlign': 'middle'},
            ),
        ], style={'textAlign': 'center', 'marginBottom': 20}),
        
        # Performance tip
        html.Div([
            html.P([
                "💡 ",
                html.Strong("Performance Tip:"),
                " Use 'No Basemap' for instant address lookups with just markers. ",
                "Use 'Light' for a clean map. ",
                "Switch to 'Detailed' for street-level detail. ",
            ], style={'fontSize': 13, 'color': '#666', 'textAlign': 'center', 'fontStyle': 'italic'})
        ], style={'marginBottom': 15}),
        
        # Radius slider above map (aligned to right edge of map)
        html.Div([
            html.Label("CIMC Site Search Radius (miles):", style={'fontWeight': 'bold', 'marginBottom': 10, 'display': 'block'}),
            dcc.Slider(
                id='radius-input',
                min=0,
                max=25,
                step=1,
                value=10,
                marks={0: '0', 5: '5', 10: '10', 15: '15', 20: '20', 25: '25'},
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], style={'width': '300px', 'marginLeft': 'auto', 'marginRight': '250px', 'marginTop': 10, 'marginBottom': 10}),
        
        # Map and GEI Score Box Container
        html.Div([
            # Map with GEI box positioned inside
            html.Div([
                dcc.Graph(
                    id='cimc-map', 
                    figure=create_default_us_map(), 
                    style={'height': '1000px', 'overflow': 'hidden'},
                    config={'responsive': True, 'displayModeBar': True}
                ),
                # GEI Score Information Box (positioned inside map's right margin)
                html.Div(id='gei-info-box', style={
                    'position': 'absolute',
                    'right': '220px',
                    'top': '570px',
                    'padding': 10,
                    'backgroundColor': '#e3f2fd',
                    'border': '2px solid #2196f3',
                    'borderRadius': 10,
                    'width': '250px',
                    'zIndex': 1000,
                    'display': 'none'  # Hidden by default
                }),
                # CIMC Site Details Box (positioned below GEI box)
                html.Div(id='cimc-details-box', style={
                    'position': 'absolute',
                    'right': '220px',
                    'top': '750px',  # Below GEI box
                    'padding': 10,
                    'backgroundColor': '#fff3e0',
                    'border': '2px solid #ff9800',
                    'borderRadius': 10,
                    'width': '250px',
                    'zIndex': 1000,
                    'display': 'none'  # Hidden by default
                })
            ], style={'width': '1650px', 'position': 'relative', 'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'marginBottom': 20, 'position': 'relative'}),
        
        # Hidden storage for CIMC data (for click callback)
        dcc.Store(id='cimc-data-store', data=None),
        
        # Hidden close button for CIMC box (actual button rendered in callback)
        html.Button(id='close-cimc-box', n_clicks=0, style={'display': 'none'}),
        
        # Data info
        html.Div([
            html.H3("GEI Score Feature Details", style={'textAlign': 'center', 'color': '#2c3e50'}),
            html.Div(id='data-info')
        ], id='data-info-container', style={'marginTop': 30, 'padding': 20, 'backgroundColor': '#f8f9fa', 'borderRadius': 5, 'display': 'none'})
        
    ], style={'padding': 20, 'maxWidth': 1800, 'margin': '0 auto'})
])

# Callback for modal control
@app.callback(
    Output('modal-container', 'style'),
    [Input('close-modal', 'n_clicks'),
     Input('about-button', 'n_clicks')],
    prevent_initial_call=False
)
def toggle_modal(close_clicks, about_clicks):
    ctx = callback_context
    
    if not ctx.triggered:
        # Show modal on initial load
        return {'display': 'block'}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'close-modal':
        # Hide modal
        return {'display': 'none'}
    elif button_id == 'about-button':
        # Show modal
        return {'display': 'block'}
    
    return {'display': 'none'}

# Callback for updating the map
@app.callback(
    [Output('cimc-map', 'figure'),
     Output('status-message', 'children'),
     Output('data-info', 'children'),
     Output('data-info-container', 'style'),
     Output('gei-info-box', 'children'),
     Output('gei-info-box', 'style'),
     Output('cimc-data-store', 'data')],
    [Input('search-button', 'n_clicks'),
     Input('address-input', 'n_submit'),  # Trigger on Enter key press
     Input('cimc-map', 'id'),  # Trigger on page load
     Input('radius-input', 'value'),  # Trigger on slider change
     Input('map-style-toggle', 'value')],  # Trigger on map style change
    [State('address-input', 'value')]
)
def update_map(n_clicks, n_submit, map_id, radius, map_style, address):
    
    if not data_loaded:
        return go.Figure(), html.Div([
            html.P("❌ CIMC_Brownfield_Final.csv not found in current directory", 
                   style={'color': 'red', 'fontWeight': 'bold'}),
            html.P("Please ensure the file is in the same folder as this dashboard.")
        ]), "", {'display': 'none'}, "", {'display': 'none'}, None
    
    if not address or not address.strip():
        # Return default US map when no address is entered
        default_map = create_default_us_map()
        return default_map, "", "", {'display': 'none'}, "", {'display': 'none'}, None
    
    # Show "Searching..." message while processing
    # (This will be replaced with final results when callback completes)
    
    # Validate inputs
    radius = max(0, min(25, radius or 10))
    
    try:
        fig, formatted_address, cimc_count, census_info, nearby_cimc = create_map_figure(
            address.strip(), 
            radius, 
            use_light_basemap=map_style
        )
        
        # Prepare CIMC data for storage (for click callback)
        cimc_store_data = None
        if nearby_cimc is not None and len(nearby_cimc) > 0:
            # Store as list of dicts with relevant fields
            cimc_store_data = nearby_cimc[['LATITUDE', 'LONGITUDE', 'PRIMARY_NAME', 'Hazard_Category', 
                                           'Hazard_Score', 'distance_miles', 'URL']].to_dict('records')
        
        # Create Data Info with Top 10 Features and their values from census tract
        if top_features_df is not None and census_info is not None:
                # Get the census tract data for the address
                lat, lon, _ = get_coordinates(address.strip())
                point = Point(lon, lat)
                containing_tracts = census_tracts_gdf[census_tracts_gdf.geometry.contains(point)]
                
                if len(containing_tracts) > 0:
                    tract_data = containing_tracts.iloc[0]
                    
                    # Create sections for each domain
                    domain_sections = []
                    for domain in ['Health', 'Socioeconomic', 'Environment']:
                        domain_features = top_features_df[top_features_df['Domain'] == domain].sort_values('Rank')
                        
                        if len(domain_features) > 0:
                            # Create table rows
                            table_rows = []
                            
                            # Add header row
                            table_rows.append(html.Tr([
                                html.Th("Feature", style={'padding': '8px', 'borderBottom': '2px solid #2c3e50', 'textAlign': 'left'}),
                                html.Th("Raw Value", style={'padding': '8px', 'borderBottom': '2px solid #2c3e50', 'textAlign': 'right'}),
                                html.Th("Percentile", style={'padding': '8px', 'borderBottom': '2px solid #2c3e50', 'textAlign': 'right'})
                            ]))
                            
                            for row in domain_features.itertuples():
                                feature_name = row.Feature
                                feature_label = row.Label
                                pctl_feature_name = f"pctl_{feature_name}"
                                
                                # Get the raw value from the tract data
                                value_str = "N/A"
                                if feature_name in tract_data.index:
                                    feature_value = tract_data[feature_name]
                                    # Format the value nicely
                                    if pd.notna(feature_value):
                                        if isinstance(feature_value, (int, np.integer)):
                                            value_str = f"{feature_value:,}"
                                        elif isinstance(feature_value, (float, np.floating)):
                                            if feature_value == -999:
                                                value_str = "N/A"
                                            else:
                                                value_str = f"{feature_value:.4f}"
                                        else:
                                            value_str = str(feature_value)
                                    else:
                                        value_str = "N/A"
                                
                                # Get the percentile value
                                pctl_str = "N/A"
                                if pctl_feature_name in tract_data.index:
                                    pctl_value = tract_data[pctl_feature_name]
                                    if pd.notna(pctl_value):
                                        if isinstance(pctl_value, (int, np.integer)):
                                            pctl_str = f"{pctl_value * 100:,.2f}"
                                        elif isinstance(pctl_value, (float, np.floating)):
                                            if pctl_value == -999:
                                                pctl_str = "N/A"
                                            else:
                                                pctl_str = f"{pctl_value * 100:.2f}"
                                        else:
                                            pctl_str = str(pctl_value)
                                    else:
                                        pctl_str = "N/A"
                                
                                # Add table row
                                table_rows.append(html.Tr([
                                    html.Td(feature_label, style={'padding': '8px', 'borderBottom': '1px solid #ddd'}),
                                    html.Td(value_str, style={'padding': '8px', 'borderBottom': '1px solid #ddd', 'textAlign': 'right'}),
                                    html.Td(pctl_str, style={'padding': '8px', 'borderBottom': '1px solid #ddd', 'textAlign': 'right'})
                                ]))
                            
                            # Create table
                            feature_table = html.Table(
                                table_rows,
                                style={
                                    'width': '100%',
                                    'borderCollapse': 'collapse',
                                    'marginTop': '10px',
                                    'backgroundColor': 'white'
                                }
                            )
                            
                            domain_sections.append(html.Div([
                                html.H5(f"{domain} Domain - Top 10 Features", 
                                       style={'color': '#00008B', 'fontWeight': 'bold', 'fontSize': '20px', 'marginTop': 15, 'marginBottom': 10}),
                                feature_table
                            ]))
                    
                    data_info = html.Div(domain_sections)
                    data_info_style = {'marginTop': 30, 'padding': 20, 'backgroundColor': '#f8f9fa', 'borderRadius': 5, 'display': 'block'}
                else:
                    data_info = html.P("Census tract not found for this address", 
                                     style={'color': '#999', 'fontStyle': 'italic'})
                    data_info_style = {'marginTop': 30, 'padding': 20, 'backgroundColor': '#f8f9fa', 'borderRadius': 5, 'display': 'block'}
        elif top_features_df is not None:
            data_info = html.P("Census tract data not available for feature values", 
                             style={'color': '#999', 'fontStyle': 'italic'})
            data_info_style = {'marginTop': 30, 'padding': 20, 'backgroundColor': '#f8f9fa', 'borderRadius': 5, 'display': 'block'}
        else:
            data_info = html.P("Top features data not available", 
                             style={'color': '#999', 'fontStyle': 'italic'})
            data_info_style = {'display': 'none'}
        
        # Create GEI info box
        if census_info:
                gei_box = html.Div([
                    html.H4("📊 GEI Scores for Search Location", style={'textAlign': 'center', 'color': '#1976d2', 'marginTop': 0, 'marginBottom': 10}),
                    html.Div([
                        html.Div([
                            html.Strong("GEI Overall Score: "),
                            html.Span(f"{census_info['gei_overall_score']:.4f}" if census_info['gei_overall_score'] != 'N/A' else 'N/A')
                        ], style={'marginBottom': 8, 'fontSize': 15}),
                        html.Div([
                            html.Strong("GEI Health Score: "),
                            html.Span(f"{census_info['gei_health_score']:.4f}" if census_info['gei_health_score'] != 'N/A' else 'N/A')
                        ], style={'marginBottom': 8, 'fontSize': 15}),
                        html.Div([
                            html.Strong("GEI Socio Score: "),
                            html.Span(f"{census_info['gei_socio_score']:.4f}" if census_info['gei_socio_score'] != 'N/A' else 'N/A')
                        ], style={'marginBottom': 8, 'fontSize': 15}),
                        html.Div([
                            html.Strong("GEI Environmental Score: "),
                            html.Span(f"{census_info['gei_env_score']:.4f}" if census_info['gei_env_score'] != 'N/A' else 'N/A')
                        ], style={'fontSize': 15})
                    ])
                ])
                gei_box_style = {
                    'position': 'absolute',
                    'right': '220px',
                    'top': '570px',
                    'padding': 10,
                    'backgroundColor': '#e3f2fd',
                    'border': '2px solid #2196f3',
                    'borderRadius': 10,
                    'width': '250px',
                    'zIndex': 1000,
                    'display': 'block'  # Show when data is available
                }
        else:
            gei_box = ""
            gei_box_style = {'display': 'none'}  # Hide when no data
            
        return fig, "", data_info, data_info_style, gei_box, gei_box_style, cimc_store_data
        
    except Exception as e:
        error_msg = html.P(f"❌ Error: {str(e)}", style={'color': 'red'})
        return go.Figure(), error_msg, "", {'display': 'none'}, "", {'display': 'none'}, None

# Callback for handling CIMC site clicks
@app.callback(
    [Output('cimc-details-box', 'children'),
     Output('cimc-details-box', 'style')],
    [Input('cimc-map', 'clickData'),
     Input('close-cimc-box', 'n_clicks')],
    [State('cimc-data-store', 'data')],
    prevent_initial_call=True
)
def handle_cimc_click(clickData, close_clicks, cimc_data):
    """Handle clicks on CIMC sites - show box for CIMC clicks, hide for base map clicks"""
    
    ctx = callback_context
    
    # Default hidden style
    hidden_style = {
        'position': 'absolute',
        'right': '220px',
        'top': '750px',
        'padding': 10,
        'backgroundColor': '#fff3e0',
        'border': '2px solid #ff9800',
        'borderRadius': 10,
        'width': '250px',
        'zIndex': 1000,
        'display': 'none'
    }
    
    visible_style = {**hidden_style, 'display': 'block'}
    
    # Check if close button was clicked
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == 'close-cimc-box':
            # Close button clicked - hide the box
            return "", hidden_style
    
    # If no click data or no CIMC data stored, hide the box
    if not clickData or not cimc_data:
        return "", hidden_style
    
    # Check if points list is empty (click on basemap with no data point)
    if 'points' not in clickData or len(clickData['points']) == 0:
        # Clicked on basemap itself - hide box
        return "", hidden_style
    
    # Get the clicked point
    point = clickData['points'][0]
    
    # Check if this is a CIMC site click using customdata (reliable for both outline and main marker)
    customdata = point.get('customdata')
    
    # Strict check: ONLY show box if customdata is present
    # Clicking on basemap, census tracts, search location, or empty space will hide the box
    if customdata is None:
        # No customdata means it's not a CIMC marker - hide box
        return "", hidden_style
    
    # Verify customdata is a list with coordinates (CIMC markers have [[lat, lon]] format)
    if not isinstance(customdata, list) or len(customdata) < 2:
        # Invalid customdata format - hide box
        return "", hidden_style
    
    # Extract lat/lon of clicked point
    clicked_lat = point.get('lat')
    clicked_lon = point.get('lon')
    
    if clicked_lat is None or clicked_lon is None:
        return "", hidden_style
    
    # Find the matching CIMC site in stored data
    # Match based on coordinates (with small tolerance for floating point comparison)
    tolerance = 0.0001
    matched_site = None
    
    for site in cimc_data:
        if (abs(site['LATITUDE'] - clicked_lat) < tolerance and 
            abs(site['LONGITUDE'] - clicked_lon) < tolerance):
            matched_site = site
            break
    
    if not matched_site:
        return "", hidden_style
    
    # Build the details box content
    site_name = matched_site.get('PRIMARY_NAME', 'N/A')
    hazard_category = matched_site.get('Hazard_Category', 'N/A')
    distance = matched_site.get('distance_miles', 'N/A')
    hazard_score = matched_site.get('Hazard_Score', 'N/A')
    url = matched_site.get('URL', '')
    
    # Format values
    distance_str = f"{distance:.2f}" if isinstance(distance, (int, float)) and distance != 'N/A' else 'N/A'
    hazard_score_str = f"{hazard_score:.2f}" if isinstance(hazard_score, (int, float)) and hazard_score != 'N/A' else 'N/A'
    
    details_content = html.Div([
        html.Div([
            html.Div([
                html.Span("Close", style={'fontSize': '11px', 'color': '#e65100', 'marginRight': '4px'}),
                html.Button("✕", id='close-cimc-box', n_clicks=0, style={
                    'backgroundColor': 'transparent',
                    'border': 'none',
                    'fontSize': '12px',
                    'color': '#e65100',
                    'cursor': 'pointer',
                    'padding': 0,
                    'lineHeight': 1
                })
            ], style={'position': 'absolute', 'right': '6px', 'top': '-12px', 'display': 'flex', 'alignItems': 'center'}),
            html.H4("🏭 Selected CIMC Site Details", style={'textAlign': 'center', 'color': '#e65100', 'marginTop': 10, 'marginBottom': 10, 'fontSize': 16})
        ], style={'position': 'relative'}),
        html.Div([
            html.Div([
                html.Strong("Site Name: "),
                html.Span(str(site_name)[:50])  # Truncate long names
            ], style={'marginBottom': 8, 'fontSize': 13}),
            html.Div([
                html.Strong("Hazard Category: "),
                html.Span(str(hazard_category))
            ], style={'marginBottom': 8, 'fontSize': 13}),
            html.Div([
                html.Strong("Distance from Search Location: "),
                html.Span(f"{distance_str} miles")
            ], style={'marginBottom': 8, 'fontSize': 13}),
            html.Div([
                html.Strong("Hazard Score: "),
                html.Span(hazard_score_str)
            ], style={'marginBottom': 8, 'fontSize': 13}),
            html.Div([
                html.Strong("URL: "),
                html.A("View Site →", href=url, target="_blank", style={'color': '#1976d2', 'textDecoration': 'none'}) if url else html.Span("N/A")
            ], style={'fontSize': 13})
        ])
    ])
    
    return details_content, visible_style

# Server configuration
server = app.server  # Expose the server for deployment

if __name__ == '__main__':
    print("="*60)
    print("GEI DASHBOARD READY")
    print("="*60)
    
    if data_loaded:
        print(f"✅ CIMC data ready")
    else:
        print("⚠️  No CIMC data loaded")
    
    if census_loaded:
        print(f"✅ Census tract data ready")
    else:
        print("⚠️  No census tract data loaded")
    
    if top_features_loaded:
        print(f"✅ Top features data ready")
    else:
        print("⚠️  No top features data loaded")
    
    print("\n🌐 Starting dashboard server...")
    print("📱 Local: http://127.0.0.1:8050")
    print("🛑 Press Ctrl+C to stop the server")
    print("="*60)
    
    # Get port from environment variable (for deployment) or use 8050 for local
    port = int(os.environ.get('PORT', 8050))
    
    # Run the app
    # debug=False for production, host='0.0.0.0' to accept external connections
    app.run(
        # debug=os.environ.get('DEBUG', 'True') == 'True',
        debug=False,
        host='0.0.0.0',
        port=port
    )