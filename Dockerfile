# Dockerfile for Geo-Equity Index Dash app
# Uses Debian-slim base and installs system deps required by GeoPandas/Fiona/GDAL

FROM python:3.10-slim

# Set non-interactive frontend for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system packages required by GDAL/PROJ/GEOS used by geopandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gdal-bin \
    libgdal-dev \
    proj-bin \
    libproj-dev \
    libgeos-dev \
    git \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables (some wheels read this)
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create app directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Expose port (can be overridden by $PORT env variable at runtime)
ENV PORT=8050
EXPOSE 8050

# Use gunicorn with the exposed WSGI 'server' object in the module
# (geo_equity_index_dashboard.py defines `server = app.server`)
CMD ["gunicorn", "geo_equity_index_dashboard:server", "--bind", "0.0.0.0:8050", "--workers", "1"]
