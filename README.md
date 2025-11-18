# Geo-Equity Index: An Interactive Environmental & Socioeconomic Health Risk Mapping Tool

A Dash/Plotly web application for mapping GEI (Geo-Equity Index) scores with details and CIMC sites with hazard scores within a specified radius of an address.

## Overview

Welcome to the Geo-Equity Index—a comprehensive tool that aggregates data from the Environmental Protection Agency (EPA), Center for Disease Control (CDC), the U.S. Census Bureau, and other authoritative sources to generate a singular health score for your neighborhood. \
The GEI score, rated from 0 (best) to 1 (worst), provides an at-a-glance assessment of environmental and socioeconomic health factors in your area.

The tool also incorporates hazardous sites as defined by the EPA's Cleanup In My Community (CIMC) program, with each site ranked on a scale of 0 to 6 (most severe) for hazard severity. \
Simply enter an address, and the interactive map will display a detailed summary of the region along with nearby hazardous sites. Below the map, a comprehensive feature table breaks down your address's score in depth, providing transparency into the underlying health metrics.

## Features

- 🗺️ **Interactive Map Visualization**: 
  - Census tract choropleth layer colored by GEI scores (Red-Yellow-Green gradient, reversed scale)
  - CIMC sites displayed with hazard score-based color coding (Yellow-Orange-Red, 0-6 scale)
  - Customizable search location marker with blue-to-magenta gradient bullseye effect
  - Dual color bars for GEI scores and CIMC hazard scores
  
- 📍 **Smart Geocoding**: 
  - Enter any address to search for nearby CIMC sites within a configurable radius
  - Address geocoding via Nominatim (OpenStreetMap API) with in-memory caching
  - Automatic census tract detection for search location
  
- 📊 **Dynamic Data Display**:
  - Adjustable search radius slider (0-25 miles) with real-time map updates
  - GEI Score box showing Overall, Health, Socio, and Environmental scores for search location
  - Top 10 Features table by domain (Health, Socioeconomic, Environment) with raw values and percentiles
  - Clickable CIMC site details box with hazard information and EPA links
  
- 🎨 **Flexible Basemap Styles**: 
  - No Basemap (fastest - white background)
  - Light (fast - minimal streets)
  - Detailed (slowest - full street detail)
  
- 🔗 **Enhanced CIMC Site Information**:
  - Hover tooltips showing site details, hazard scores, and distance from search location
  - Click on any CIMC marker to open details box with comprehensive site information
  - Direct links to EPA site pages for detailed hazard documentation
  
- 📈 **Census Tract Intelligence**: 
  - Hover over search location to see GEI scores and census tract metadata
  - Automatic detection of census tract containing the search address
  - Feature values extracted directly from shapefile data

## Data Requirements

The application requires three data files in the `data/` directory:

1. **CIMC_Sites_Hazard_Score.csv** - CSV file with CIMC site locations and hazard scores
   - *Note: This file was generated from the analysis in the `analysis/CIMC EDA and Hazard Score.ipynb` notebook.*
   - *The notebook processes raw data (`Cleanups.gdb`) from the EPA. The raw data can be downloaded from: https://dmap-prod-oms-edc.s3.amazonaws.com/index.html#OLEM/OLEM-OPM/*
   - Required columns: `LATITUDE`, `LONGITUDE`, `Hazard_Score`
   - Optional columns: `Site_Name`, `Status`, `Type`, `Address`, `City`, `State`, `URL`

2. **census_tracts_with_gei.gpkg** - GeoPackage with census tract data and GEI scores (stored with Git LFS)
   - Required columns: `GEI_overall_score`, `GEI_health_score`, `GEI_socio_score`, `GEI_env_score`
   - Additional columns: `GEOID`, `Census Tract`, `County`, `State`, `StateDesc`
   - Feature columns with `pctl_` prefix for percentile values (0-1 scale, displayed as 0-100)
   - Contains ~73,000 U.S. census tracts
   - GeoPackage format is optimized for fast loading of large spatial datasets (173 MB)
   - Managed via Git LFS for efficient repository storage

3. **GEI_top10_features_2025-11-14.csv** - Top 10 features by domain
   - Required columns: `Feature`, `Label`, `Domain`, `Rank`
   - Used to display feature-specific data for the search location
   - Features organized by Health, Socioeconomic, and Environment domains

## Live Demo

The application is currently deployed at: **https://geo-equity-index-dashboard.onrender.com/**

*Note: The free tier on Render may experience cold starts (30-60 second initial load) if the service has been inactive.*

## Local Development

### Prerequisites

- Python 3.10 or higher
- pip or conda
- Git LFS (for downloading large data files)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aessa7/CSE6242OAN_Final_Project_Team86.git
   cd CSE6242OAN_Final_Project_Team86
   ```

2. Install Git LFS and fetch large files:
   ```bash
   git lfs install
   git lfs pull
   ```

3. Create a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   # or
   source .venv/bin/activate     # macOS/Linux
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the app:
   ```bash
   python geo_equity_index_dashboard.py
   ```

6. Open your browser to `http://127.0.0.1:8050`

## Deployment

### Option A: Docker (Recommended)

The repository includes a `Dockerfile` that automatically installs all system dependencies (GDAL, PROJ, GEOS) required by GeoPandas.

#### Local Docker Build & Test

```bash
# Build the image
docker build -t geiq-dashboard:latest .

# Run the container
docker run -p 8050:8050 geiq-dashboard:latest

# Open http://localhost:8050
```

#### Deploy to Render (or Railway/Fly.io)

1. Push your repository to GitHub (if not already done):
   ```bash
   git add .
   git commit -m "Update to use GeoPackage for faster loading"
   git push origin main
   ```

2. Go to [Render.com](https://render.com) and sign up (free tier available)

3. Click **"New +"** → **"Web Service"** and connect your GitHub repository

4. Configure the service:
   - **Name**: `geo-equity-dashboard`
   - **Environment**: Docker
   - **Build Command**: (leave default or blank; Render auto-detects Dockerfile)
   - **Start Command**: (leave blank; Dockerfile has CMD)
   - **Instance Type**: Free tier works for testing; upgrade for production
   - **Environment Variables**: (none required; PORT is auto-set)

5. Click **"Create Web Service"** and wait for deployment (3-5 minutes)

6. Once deployed, Render provides a public URL (e.g., `https://geo-equity-dashboard.onrender.com`)

## Performance Tips

- **Data Loading**: GeoPackage format (.gpkg) is used for fast census tract loading (~173 MB, loads in <30 seconds)
- **Git LFS**: Large data files are managed with Git LFS for efficient repository storage
- **Basemap Selection**: 
  - "No Basemap" (white-bg) - instant address lookups with just data markers (fastest)
  - "Light" (carto-positron) - good balance of performance and map context (fast)
  - "Detailed" (open-street-map) - full street-level detail (slowest)
- **Geocoding Cache**: Addresses are cached in memory (`geocode_cache` dictionary) for instant re-use
- **Feature Display**: GEI feature details are dynamically loaded only when an address is searched
- **Percentile Formatting**: Percentile values (stored as 0-1) are automatically converted to 0-100 scale with 2 decimal places
- **Code Optimizations**: 
  - Vectorized distance calculations for radius filtering (5-10x faster than naive iteration)
  - `itertuples()` instead of `iterrows()` for DataFrame iteration (10-100x faster, used for CIMC marker processing and feature table generation)
  - Bounding box pre-filtering for census tract spatial queries (20% buffer to capture edge tracts)
- **Geocoding**: Uses Nominatim (free, no API keys required). For production with high traffic, consider paid geocoding APIs (Mapbox, Google Places) or self-hosted Nominatim instance

## Troubleshooting

### Issue: Address geocoding fails
- Check internet connection (Nominatim requires external API calls)
- Try a more complete address (street, city, state, zip)

### Issue: Map loads slowly on startup
- This is normal with large census tract datasets. The initial load may take 20-30 seconds

## Technologies Used

- **Frontend**: Dash, Plotly (interactive maps and visualizations)
- **Backend**: Python, Flask (underlying Dash framework)
- **Geospatial**: GeoPandas, Shapely, GDAL, Fiona
- **Data Formats**: GeoPackage (.gpkg), GeoJSON, Shapefile
- **Geocoding**: Geopy (Nominatim)
- **Data**: Pandas, NumPy
- **Analysis**: Matplotlib, Seaborn, Contextily
- **Serving**: Gunicorn (production WSGI server)
- **Containerization**: Docker

## Project Structure

```
CSE6242OAN_Final_Project_Team86/
├── geo_equity_index_dashboard.py          # Main Dash app
├── gei_visualization_details.md           # Technical documentation of visualization approach
├── requirements.txt                       # Python dependencies
├── Dockerfile                             # Docker image definition
├── Procfile                               # Procfile for deployment
├── .dockerignore                          # Files to exclude from Docker build
├── .gitattributes                         # Git LFS tracking configuration
├── .gitignore                             # Git ignore rules
├── README.md                              # This file
├── data/
│   ├── CIMC_Sites_Hazard_Score.csv        # CIMC site locations and hazard scores
│   ├── census_tracts_with_gei.gpkg        # Census tracts with GEI (Git LFS, 173 MB)
│   └── GEI_top10_features_2025-11-14.csv  # Top 10 features by domain
└── analysis/
    ├── CIMC EDA and Hazard Score.ipynb    # CIMC EDA and hazard score generation
    └── merge_census_tract_with_gei_data.py # Script to merge GEI data with census tracts
```

## License



## Contact

For questions or issues, please contact: aessa7@gatech.edu, blarkin31@gatech.edu
