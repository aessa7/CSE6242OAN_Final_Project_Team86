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

def get_coordinates(address):
    """Geocode an address to lat/lon with caching"""
    # Check cache first
    if address in geocode_cache:
        print(f"✓ Using cached coordinates for: {address[:50]}...")
        return geocode_cache[address]
    
    try:
        location = geolocator.geocode(address)
        if location:
            result = (location.latitude, location.longitude, location.address)
            geocode_cache[address] = result  # Cache the result
            return result
        return None, None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None, None

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
                'name': tract.get('NAME', 'N/A'),
                'state': tract.get('STUSPS', 'N/A'),
                'gei_score': tract.get('GEI_overall_score', 'N/A'),
            }
            
            print(f"✓ Found census tract: GEOID={info['geoid']}, GEI={info['gei_score']}")
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
    
    # Calculate distances
    distances = []
    valid_indices = []
    
    for idx, row in cimc_data.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            if pd.notna(lat) and pd.notna(lon):
                dist = haversine_distance(center_lat, center_lon, lat, lon)
                if dist <= radius_miles:
                    distances.append(dist)
                    valid_indices.append(idx)
        except (ValueError, TypeError):
            continue
    
    if valid_indices:
        filtered_df = cimc_data.loc[valid_indices].copy()
        filtered_df['distance_miles'] = distances
        return filtered_df.sort_values('distance_miles')
    
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
    lat, lon, formatted_address = get_coordinates(address)
    
    if lat is None or lon is None:
        # Return empty figure with error message
        fig = go.Figure()
        fig.add_annotation(
            text=f"Could not find coordinates for: {address}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Error: Address Not Found",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig, f"Address not found: {address}", 0
    
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
                    colorscale='Blues',  # Light blue to dark blue gradient
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
                        y=0.5  # Align with CIMC colorbar top
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
        
        for idx, point in nearby_cimc.iterrows():
            try:
                point_lat = float(point[lat_col])
                point_lon = float(point[lon_col])
                
                # Create hover text
                hover_text = f"CIMC Site<br>Distance: {point['distance_miles']:.1f} miles"
                
                # Add hazard score if available
                if 'Hazard_Score' in point and pd.notna(point['Hazard_Score']):
                    hazard_score = float(point['Hazard_Score'])
                    hover_text += f"<br>Hazard Score: {hazard_score:.2f}"
                    cimc_hazard_scores.append(hazard_score)
                else:
                    cimc_hazard_scores.append(None)
                
                # Add other available information
                info_fields = ['Site_Name', 'Status', 'Type', 'Address', 'City', 'State']
                for field in info_fields:
                    if field in point and pd.notna(point[field]):
                        hover_text += f"<br>{field}: {point[field]}"
                
                cimc_lats.append(point_lat)
                cimc_lons.append(point_lon)
                cimc_texts.append(hover_text)
                    
            except (ValueError, KeyError):
                continue
        
        # Add CIMC points to map
        if cimc_lats:
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
                        y=0.5  # Align with GEI colorbar
                    ),
                    showscale=True
                ),
                text=cimc_texts,
                hoverinfo='text'
            ))
    
    # Layer 3: Add search location marker LAST (marker on top of everything)
    print(f"🎯 Adding address marker at: lat={lat}, lon={lon}")  # Debug print
    
    # Get census tract info for the search address
    census_info = get_census_tract_info(lat, lon)
    
    # Build hover text with census tract info
    hover_text = f"📍 Search Location<br>{formatted_address}"
    if census_info:
        hover_text += f"<br><br><b>GEI Score Info:</b>"
        hover_text += f"<br>GEOID: {census_info['geoid']}"
        hover_text += f"<br>Name: {census_info['name']}"
        hover_text += f"<br>State: {census_info['state']}"
        if census_info['gei_score'] != 'N/A':
            hover_text += f"<br>GEI Score: {census_info['gei_score']:.4f}"
        else:
            hover_text += f"<br>GEI Score: {census_info['gei_score']}"
    else:
        hover_text += "<br><br>⚠️ Census tract information not available"
    
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers+text',  # Add text to make it even more visible
        marker=dict(
            size=20,  # Larger size
            color='magenta',  # Bright magenta color to stand out
            opacity=1.0,  # Full opacity
            symbol='circle',  # Filled circle
        ),
        text=['📍'],  # Pin emoji as text
        textfont=dict(size=30, color='red'),
        textposition='top center',
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
        margin=dict(l=0, r=250, t=30, b=0),  # Increased right margin for colorbars
        title=f"CIMC Sites within {radius_miles} miles of {formatted_address[:50]}...",
        hoverlabel=dict(
            bgcolor="white",  # White background
            bordercolor="black",  # Black border
            font=dict(color="black", size=13),  # Black text
            namelength=-1  # Show full text
        )
    )
    
    return fig, formatted_address, cimc_count

# Load data on startup
print("="*60)
print("LOADING DATA AT STARTUP")
print("="*60)
data_loaded = load_cimc_data()
census_loaded = load_census_tracts()
print("="*60)

# Define the app layout
app.layout = html.Div([
    html.Div([
        html.H1("Geo-Equity Index: \n \
       An Interactive Environmental & Socioeconomic Health Risk Mapping Tool",
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 30}),
        
        # Input controls
        html.Div([
            html.Label("Enter Address:", style={'fontWeight': 'bold', 'marginBottom': 5}),
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
        
        # Status message
        html.Div(id='status-message', style={'marginBottom': 20, 'textAlign': 'center'}),
        
        # Performance tip
        html.Div([
            html.P([
                "💡 ",
                html.Strong("Performance Tip:"),
                " Use 'No Basemap' for instant address lookups with just markers. ",
                "Use 'Light' for a clean map. ",
                "Switch to 'Detailed' for street-level detail. ",
                "Addresses are cached for instant re-use."
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
        
        # Map
        html.Div([
            dcc.Graph(
                id='cimc-map', 
                figure=create_default_us_map(), 
                style={'height': '1000px', 'overflow': 'hidden'},
                config={'responsive': True, 'displayModeBar': True}
            )
        ], style={'marginBottom': 20, 'position': 'relative', 'overflow': 'hidden'}),
        
        # Data info
        html.Div([
            html.H3("Data Information"),
            html.Div(id='data-info')
        ], style={'marginTop': 30, 'padding': 20, 'backgroundColor': '#f8f9fa', 'borderRadius': 5}),
        
        # Map parameters info box (temporary for debugging)
        html.Div(id='map-params-info', style={
            'marginTop': 20,
            'padding': 10, 
            'backgroundColor': '#fff3cd', 
            'border': '1px solid #ffc107',
            'borderRadius': 5,
            'fontFamily': 'monospace',
            'fontSize': 12
        })
        
    ], style={'padding': 20, 'maxWidth': 1800, 'margin': '0 auto'})
])

# Callback for live map parameters display
@app.callback(
    Output('map-params-info', 'children'),
    Input('cimc-map', 'relayoutData')
)
def display_live_map_params(relayout_data):
    if relayout_data is None:
        return "🗺️ Map Parameters: Move or zoom the map to see current settings"
    
    # Extract center and zoom from relayout data
    info_parts = []
    
    # Check for map.center (this is the correct key for Scattermap)
    if 'map.center' in relayout_data:
        center = relayout_data['map.center']
        if isinstance(center, dict):
            lat = center.get('lat')
            lon = center.get('lon')
            if lat is not None:
                info_parts.append(f"Center Lat: {lat:.4f}")
            if lon is not None:
                info_parts.append(f"Center Lon: {lon:.4f}")
    
    # Check for map.zoom
    if 'map.zoom' in relayout_data:
        zoom = relayout_data['map.zoom']
        info_parts.append(f"Zoom: {zoom:.2f}")
    
    if info_parts:
        return html.Div([
            html.Strong("🗺️ Current Map View: ", style={'color': '#2c3e50'}),
            html.Span(" | ".join(info_parts), style={'fontFamily': 'monospace', 'fontSize': '14px', 'color': '#27ae60'})
        ])
    else:
        # Show all available keys for debugging
        return html.Div([
            html.Strong("🗺️ Map Data: ", style={'color': '#2c3e50'}),
            html.Span(f"Keys detected: {', '.join(str(k) for k in relayout_data.keys())}", 
                     style={'fontSize': '12px', 'fontStyle': 'italic'})
        ])

# Callback for updating the map
@app.callback(
    [Output('cimc-map', 'figure'),
     Output('status-message', 'children'),
     Output('data-info', 'children')],
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
        ]), ""
    
    if not address or not address.strip():
        # Return default US map when no address is entered
        default_map = create_default_us_map()
        return default_map, html.P("Enter an address to search for CIMC sites", 
                                   style={'color': '#3498db', 'fontSize': 16}), ""
    
    # Validate inputs
    radius = max(0, min(25, radius or 10))
    
    try:
        fig, formatted_address, cimc_count = create_map_figure(
            address.strip(), 
            radius, 
            use_light_basemap=map_style
        )
        
        if cimc_count >= 0:
            status_msg = html.Div([
                html.P(f"✅ Found {cimc_count} CIMC sites within {radius} miles of:", 
                       style={'color': 'green', 'fontWeight': 'bold', 'marginBottom': 5}),
                html.P(f"{formatted_address}", style={'fontStyle': 'italic'})
            ])
            
            map_style_label = {
                'none': 'No Basemap (Fastest)',
                'light': 'Fast (Light)',
                'detailed': 'Detailed'
            }.get(map_style, map_style)
            
            data_info = html.Div([
                html.P(f"Total CIMC records in database: {len(cimc_data) if cimc_data is not None else 0}"),
                html.P(f"Sites found within search radius: {cimc_count}"),
                html.P(f"Search radius: {radius} miles"),
                html.P(f"Map style: {map_style_label}", 
                       style={'fontStyle': 'italic', 'color': '#666'})
            ])
        else:
            status_msg = html.P("❌ Address not found", style={'color': 'red'})
            data_info = ""
            
        return fig, status_msg, data_info
        
    except Exception as e:
        error_msg = html.P(f"❌ Error: {str(e)}", style={'color': 'red'})
        return go.Figure(), error_msg, ""

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
    
    print("\n🌐 Starting dashboard server...")
    print("📱 Local: http://127.0.0.1:8050")
    print("🛑 Press Ctrl+C to stop the server")
    print("="*60)
    
    # Get port from environment variable (for deployment) or use 8050 for local
    port = int(os.environ.get('PORT', 8050))
    
    # Run the app
    # debug=False for production, host='0.0.0.0' to accept external connections
    app.run(
        debug=os.environ.get('DEBUG', 'True') == 'True',
        host='0.0.0.0',
        port=port
    )