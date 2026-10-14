#Yasmine RAZAVI EBRAHIMI : ysre@ulaval.ca

import os
import xarray as xr
import pandas as pd

# Define root directories
root_dir = "C:/Users/danyblanchet7/Desktop/Data analysis"
main_dir = root_dir + "/ERA5" 
out_dir  = root_dir + "/Extraction_SM" # Output directory

# Directories to process
directories = [
    'surface_pressure',
    'dew_temp',
    'air_temp',
    'total_precipitation',
    'surface_thermal_radiation_downward',
    'surface_solar_radiation_downward',
    '10m_u_component_wind',
    '10m_v_component_wind',
    'snow_depth',
    'snow_density',
    'snow_melt',
    'snow_water_equivalent',
    'potential_evaporation',
    'volumetric_soil_water',
]

points = [
    {
        'name': 'SainteMarthe-2020s-EVAP',
        'lon_min': -74.25,
        'lon_max': -74.25,
        'lat_min': 45.40,
        'lat_max': 45.40
    }
] 

# Function to process a single point
def process_point(point):
    name = point['name']
    lon_min = point['lon_min']
    lon_max = point['lon_max']
    lat_min = point['lat_min']
    lat_max = point['lat_max']

    point_dir = os.path.join(out_dir, name.replace(' ', '_'))
    os.makedirs(point_dir, exist_ok=True)

    for directory in directories:
        dir_path = os.path.join(main_dir, directory)
        point_dir_path = os.path.join(point_dir, directory)
        os.makedirs(point_dir_path, exist_ok=True)

        if not os.path.exists(dir_path):
            print(f"Directory does not exist: {dir_path}")
            continue

        for file_name in os.listdir(dir_path):
            if file_name.endswith('.nc'):
                file_path = os.path.join(dir_path, file_name)
                with xr.open_dataset(file_path) as ds:
                    print(f"Processing {file_name}")

                    if 'lon' in ds.coords and 'lat' in ds.coords:
                        ds_subset = ds.sel(lat=lat_min, lon=lon_min, method="nearest")
                        print(ds_subset)

                        # Save the subset to the specific point's folder
                        output_filename = f"subset_{name.replace(' ', '_')}_{file_name}"
                        output_filepath = os.path.join(point_dir_path, output_filename)
                        ds_subset.to_netcdf(output_filepath)
                        print(f"Saved subset to {output_filepath}")
                    else:
                        print(f"Coordinate names 'longitude' and 'latitude' not found in {file_path}. Please adjust the coordinate names accordingly.")

# Process each point
for point in points:
    process_point(point)
