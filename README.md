# Geo-Equity Index: An Interactive Environmental & Socioeconomic Health Risk Mapping Tool

A Dash/Plotly web application for mapping GEI (Geo-Equity Index) scores and CIMC sites with hazard scores within a specified radius of an address.

## Features

- 🗺️ Interactive map visualization with census tract data (GEI scores) and CIMC sites (hazard scores)
- 📍 Geocoding: Enter any address to search for nearby CIMC sites within a configurable radius
- 📊 Real-time filtering: Adjust the search radius with a slider to dynamically update results
- 🎨 Multiple basemap styles: Choose between no basemap (fastest), light, or detailed maps
- 💾 Address geocoding cache: Repeated addresses are cached for instant lookups
- 📈 Census Tract Info: Hover over the search location to see GEI score and census tract information

## Data Requirements

The application requires two data files in the `data/` directory:

1. **CIMC_Sites_Hazard_Score.csv** - CSV file with CIMC site locations and hazard scores
   - Required columns: `LATITUDE`, `LONGITUDE`, `Hazard_Score`
   - Optional columns: `Site_Name`, `Status`, `Type`, `Address`, `City`, `State`

2. **census_tracts_with_gei.gpkg** - GeoPackage with census tract data and GEI scores
   - Required columns: `GEI_overall_score` (overall GEI score)
   - Additional columns: `GEOID`, `NAME`, `STUSPS` (state code)
   - GeoPackage format is optimized for fast loading of large spatial datasets
   - Alternative: `census_tracts_with_gei.geojson` (if GeoPackage unavailable, but slower)

## Local Development

### Prerequisites

- Python 3.10 or higher
- pip or conda

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aessa7/CSE6242OAN_Final_Project.git
   cd CSE6242OAN_Final_Project
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   # or
   source .venv/bin/activate     # macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:
   ```bash
   python geo_equity_index_dashboard.py
   ```

5. Open your browser to `http://127.0.0.1:8050`

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
   - **Name**: `geo-equity-dashboard` (or your choice)
   - **Environment**: Docker
   - **Build Command**: (leave default or blank; Render auto-detects Dockerfile)
   - **Start Command**: (leave blank; Dockerfile has CMD)
   - **Instance Type**: Free tier works for testing; upgrade for production
   - **Environment Variables**: (none required; PORT is auto-set)

5. Click **"Create Web Service"** and wait for deployment (3-5 minutes)

6. Once deployed, Render provides a public URL (e.g., `https://geo-equity-dashboard.onrender.com`)

## Performance Tips

- **Data Loading**: GeoPackage format (.gpkg) is used for fast census tract loading (~173 MB, loads in <30 seconds)
- **Basemap Selection**: Use "No Basemap" for instant address lookups; "Light" is a good balance; "Detailed" is slowest but shows streets
- **Geocoding Cache**: Addresses are cached in memory. For production, consider a Redis cache for multi-instance deployments
- **Nominatim Rate Limits**: The app uses Nominatim (free geocoding). For high-traffic production apps, consider a paid geocoding API (Mapbox, Google Places)

## Troubleshooting

### Issue: "CIMC_Sites_Hazard_Score.csv not found"
- Ensure the CSV file is in the `data/` directory
- Check file name spelling and case

### Issue: "census_tracts_with_gei.gpkg not found"
- Ensure the GeoPackage file is in the `data/` directory
- If using GeoJSON instead, ensure `census_tracts_with_gei.geojson` is present
- GeoPackage is recommended for better performance

### Issue: Address geocoding fails
- Check internet connection (Nominatim requires external API calls)
- Try a more complete address (street, city, state, zip)

### Issue: Map loads slowly on startup
- This is normal with large census tract datasets. The initial load may take 20-30 seconds
- Subsequent searches use cached geocoding for faster results
- Consider using a simpler dataset for testing if needed

### Issue: Census tract information not showing in tooltip
- Ensure the GeoPackage contains the `GEI_overall_score`, `GEOID`, `NAME`, and `STUSPS` columns
- Check that the search address is within the coverage area of the census tracts

## Technologies Used

- **Frontend**: Dash, Plotly (interactive maps and visualizations)
- **Backend**: Python, Flask (underlying Dash framework)
- **Geospatial**: GeoPandas, Shapely, GDAL, Fiona
- **Data Formats**: GeoPackage (.gpkg), GeoJSON, Shapefile
- **Geocoding**: Geopy (Nominatim)
- **Data**: Pandas, NumPy
- **Serving**: Gunicorn (production WSGI server)
- **Containerization**: Docker

## Project Structure

```
CSE6242OAN_Final_Project/
├── geo_equity_index_dashboard.py  # Main Dash app
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image definition
├── Procfile                       # Procfile for deployment
├── .dockerignore                  # Files to exclude from Docker build
├── README.md                      # This file
└── data/
    ├── CIMC_Sites_Hazard_Score.csv
    ├── census_tracts_with_gei.gpkg        # Primary: GeoPackage (fast)
    ├── census_tracts_with_gei.geojson     # Alternative: GeoJSON (slower)
    ├── census_tracts_with_gei.shp         # Original shapefile components
    ├── census_tracts_with_gei.shx
    ├── census_tracts_with_gei.dbf
    ├── census_tracts_with_gei.prj
    └── census_tracts_with_gei.cpg
```

## License

[Add license information here]

## Contact

For questions or issues, please contact: [Your contact info]
