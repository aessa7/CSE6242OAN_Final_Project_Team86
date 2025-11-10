# Geo-Equity Index: An Interactive Environmental & Socioeconomic Health Risk Mapping Tool

A Dash/Plotly web application for mapping GEI (Geo-Equity Index) scores and CIMC sites with hazard scores within a specified radius of an address.

## Features

- 🗺️ Interactive map visualization with census tract data (GEI scores) and CIMC sites (hazard scores)
- 📍 Geocoding: Enter any address to search for nearby CIMC sites within a configurable radius
- 📊 Real-time filtering: Adjust the search radius with a slider to dynamically update results
- 🎨 Multiple basemap styles: Choose between no basemap (fastest), light, or detailed maps
- 💾 Address geocoding cache: Repeated addresses are cached for instant lookups

## Data Requirements

The application requires two data files in the `data/` directory:

1. **CIMC_Sites_Hazard_Score.csv** - CSV file with CIMC site locations and hazard scores
   - Required columns: `LATITUDE`, `LONGITUDE`, `Hazard_Score`
   - Optional columns: `Site_Name`, `Status`, `Type`, `Address`, `City`, `State`

2. **census_tracts_with_eji.shp** - Shapefile with census tract data and EJI scores
   - Required columns: `RPL_EJI_CB` (EJI score)
   - The app will auto-convert to EPSG:4326 if needed
   - All shapefile components must be present: `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`

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
   git commit -m "Add Dockerfile and deployment files"
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

#### Deploy to Railway.app (Alternative)

1. Go to [Railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository and authorize
4. Railway auto-detects the Dockerfile and deploys

#### Deploy to Fly.io (Alternative)

1. Install flyctl: https://fly.io/docs/getting-started/installing-flyctl/
2. Run: `flyctl launch` in your project directory
3. Follow prompts and deploy: `flyctl deploy`

### Option B: Without Docker (For Heroku or other platforms with system libs)

If your hosting platform supports system libraries (GDAL, PROJ), you can use `requirements.txt` + `Procfile`:

```bash
# On Heroku:
git push heroku main
```

Note: Most free hosting platforms lack GDAL/PROJ by default. Docker (Option A) is more reliable.

## Performance Tips

- **Basemap Selection**: Use "No Basemap" for instant address lookups; "Light" is a good balance; "Detailed" is slowest but shows streets.
- **Geocoding Cache**: Addresses are cached in memory. For production, consider a Redis cache for multi-instance deployments.
- **Shapefile Size**: If census tract loading is slow, consider simplifying the shapefile or converting to GeoJSON.
- **Nominatim Rate Limits**: The app uses Nominatim (free geocoding). For high-traffic production apps, consider a paid geocoding API (Mapbox, Google Places).

## Troubleshooting

### Issue: "CIMC_Sites_Hazard_Score.csv not found"
- Ensure the CSV file is in the `data/` directory
- Check file name spelling and case

### Issue: "census_tracts_with_eji.shp not found"
- Ensure all shapefile components are in the `data/` directory (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`)
- Check file name spelling and case

### Issue: Address geocoding fails
- Check internet connection (Nominatim requires external API calls)
- Try a more complete address (street, city, state, zip)

### Issue: Map loads slowly with large shapefiles
- Switch to "No Basemap" or "Light" basemap
- Consider pre-computing and caching map tiles
- Simplify the shapefile (reduce polygon complexity)

## Technologies Used

- **Frontend**: Dash, Plotly (interactive maps and visualizations)
- **Backend**: Python, Flask (underlying Dash framework)
- **Geospatial**: GeoPandas, Shapely, Geopandas, Fiona, GDAL
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
    ├── census_tracts_with_eji.shp
    ├── census_tracts_with_eji.shx
    ├── census_tracts_with_eji.dbf
    ├── census_tracts_with_eji.prj
    └── census_tracts_with_eji.cpg
```

## License

[Add license information here]

## Contact

For questions or issues, please contact: [Your contact info]
