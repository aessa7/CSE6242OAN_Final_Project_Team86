"""
Census Tract with GEI Data Processing Script
This script loads census tract data, merges it with calculated GEI scores, and exports to geospatial files in various formats.
"""

# Import required libraries
import pandas as pd

# Import geospatial libraries
import geopandas as gpd


# Display all columns and rows for better visibility
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


def main():
    # List layers in the GDB file
    gdb_path = "Data/cb_2020_us_all_500k.gdb"
    
    gdb_layers = gpd.list_layers(gdb_path)
    print("Layers in the GDB file:")
    print(gdb_layers)
    
    # Read the census tract layer
    tract_layer = "cb_2020_us_tract_500k"
    gdf_tracts = gpd.read_file(gdb_path, layer=tract_layer)
    
    print(f"Loaded {len(gdf_tracts)} census tracts")
    print(f"Columns: {list(gdf_tracts.columns)}")
    print(f"\nFirst few rows:")
    print(gdf_tracts.head(3))
    
    # Read in gei data
    gei_data_path = "GEI_Dashboard/data/GEI_scores_2025-11-14.csv"
    gei_df = pd.read_csv(gei_data_path, dtype={"GEOID": str})
    print(f"Loaded GEI data with {len(gei_df)} records")
    print(f"Columns: {list(gei_df.columns)}")
    print(f"\nFirst few rows:")
    print(gei_df.head(3))
    
    # Merge gei data with census tracts on GEOID
    gdf_tracts_gei = gdf_tracts.merge(gei_df, on="GEOID", how="left")
    
    print(f"Merged dataset has {len(gdf_tracts_gei)} records")
    print(f"Columns: {list(gdf_tracts_gei.columns)}")
    print(f"\nFirst few rows:")
    print(gdf_tracts_gei.head(3))
    
    # Drop any columns with suffix _y from gdf_tracts_gei
    gdf_tracts_gei = gdf_tracts_gei.loc[:, ~gdf_tracts_gei.columns.str.endswith('_y')]
    
    # Also rename _x suffix columns back to original names
    gdf_tracts_gei.columns = gdf_tracts_gei.columns.str.replace('_x$', '', regex=True)
    
    # Define columns to keep
    keep_cols = [
        'GEOID',
        'NAME',
        'Census Tract',
        'County',
        'State',
        'StateDesc',
        'geometry',
        'E_MHLTH',
        'Current Lack of Health Insurance',
        'Alcohol Abuse',
        'Covid-19 Vaccination Rates',
        'Proximity to Nursing Homes',
        'E_ASTHMA',
        'Proximity to hospitals ',
        'Child Mortality',
        'E_DIABETES',
        'Drug Overdose Deaths per 100,000 People',
        'Tax Base: Median Real Estate Taxes Paid',
        'Below Poverty',
        'No Vehicle',
        'Percent of Household with no internet access',
        'Gun Violence',
        'Homeless Population',
        'Single-Parent Households',
        'Residential Energy Cost Burden',
        'Religious Organizations',
        'Percent of Housing Units Built Between 1940-1969 as of 2015-2019',
        'Deaths from climate disasters',
        'Brownfields',
        'Increased PM2.5 mortality - CVD (ages 65+)',
        'E_HOUAGE',
        'Impermeable Surfaces',
        'Risk Management Plan Facilities',
        'Metal Recyclers',
        'Expected Annual Loss - Building Value',
        'Traffic Proximity and Volume',
        'Chemical Manufacturers',
        'GEI_overall_score',
        'GEI_health_score',
        'GEI_socio_score',
        'GEI_env_score',
        'pctl_E_MHLTH',
        'pctl_Current Lack of Health Insurance',
        'pctl_Alcohol Abuse',
        'pctl_Covid-19 Vaccination Rates',
        'pctl_Proximity to Nursing Homes',
        'pctl_E_ASTHMA',
        'pctl_Proximity to hospitals ',
        'pctl_Child Mortality',
        'pctl_E_DIABETES',
        'pctl_Drug Overdose Deaths per 100,000 People',
        'pctl_Tax Base: Median Real Estate Taxes Paid',
        'pctl_Below Poverty',
        'pctl_No Vehicle',
        'pctl_Percent of Household with no internet access',
        'pctl_Gun Violence',
        'pctl_Homeless Population',
        'pctl_Single-Parent Households',
        'pctl_Residential Energy Cost Burden',
        'pctl_Religious Organizations',
        'pctl_Percent of Housing Units Built Between 1940-1969 as of 2015-2019',
        'pctl_Deaths from climate disasters',
        'pctl_Brownfields',
        'pctl_Increased PM2.5 mortality - CVD (ages 65+)',
        'pctl_E_HOUAGE',
        'pctl_Impermeable Surfaces',
        'pctl_Risk Management Plan Facilities',
        'pctl_Metal Recyclers',
        'pctl_Expected Annual Loss - Building Value',
        'pctl_Traffic Proximity and Volume',
        'pctl_Chemical Manufacturers',
    ]
    
    print(f"Cleaned columns: {list(gdf_tracts_gei.columns)}")
    print(f"\nAll columns: {gdf_tracts_gei.columns.tolist()}")
    
    # Export the merged data to various formats
    gdf_tracts_gei = gdf_tracts_gei[keep_cols]
    
    # 1. GeoJSON - Best for web mapping (Leaflet, Mapbox, etc.)
    gdf_tracts_gei.to_file("Data/census_tracts_with_gei.geojson", driver="GeoJSON")
    print("✓ Exported to GeoJSON")
    
    # 2. Shapefile - Most compatible with GIS software (ArcGIS, QGIS)
    gdf_tracts_gei.to_file("Data/census_tracts_with_gei.shp")
    print("✓ Exported to Shapefile")
    
    # 3. GeoPackage - Modern format, no column name limits
    gdf_tracts_gei.to_file("Data/census_tracts_with_gei.gpkg", driver="GPKG")
    print("✓ Exported to GeoPackage")
    
    print("\n✓ All exports complete!")
    
    # Display GEI data statistics
    print("\nGEI Data Statistics:")
    print(gei_df.describe())
    
    print("\nEND")


if __name__ == "__main__":
    main()
