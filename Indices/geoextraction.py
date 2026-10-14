#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExtractPoint_ERA5.py
=====================
Written by: Yasmine RAZAVI EBRAHIMI (ysre@ulaval.ca)

Extrait, pour UN SEUL point (le pixel de grille ERA5-Land le plus
proche), toutes les variables necessaires au calcul des indices de
secheresse SAMI/SSMI (et variables complementaires).

CORRECTION par rapport a la version precedente :
  - ds.sel(lon=slice(lon_min, lon_max), ...) avec lon_min == lon_max
    ne retourne un resultat que si cette coordonnee EXACTE existe dans
    la grille - ce qui est tres improbable pour des coordonnees
    "reelles" (ex: -71.167297) sur une grille a resolution ~0.1deg.
    Resultat : un dataset VIDE, sans erreur explicite.
  - Corrige ici via ds.sel(..., method="nearest") sur un point unique
    (pas un slice), qui prend toujours le pixel de grille le plus
    proche des coordonnees demandees.

Une fois extrait, chaque variable devient une serie temporelle 1D
(un seul pixel) -> le calcul des indices SAMI/SSMI sur ce point sera
quasi instantane (secondes), sans besoin de Dask/chunking spatial.
"""

import os
import xarray as xr

# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------

root_dir = "C:/Users/danyblanchet7/Desktop/Data analysis"
main_dir = os.path.join(root_dir, "ERA5")
out_dir = os.path.join(root_dir, "Yasmine")  # Dossier de sortie

# Dossiers a traiter. AJOUTEZ ICI le dossier d'humidite du sol si vous
# voulez calculer le SSMI (ex: 'volumetric_soil_water') - verifiez son
# nom exact sous main_dir avant de lancer.
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

    # 'volumetric_soil_water',  # <- decommentez et verifiez le nom exact
]

# Point(s) a extraire : lat/lon en degres decimaux (coordonnees reelles,
# PAS besoin de min/max identiques - le pixel le plus proche est trouve
# automatiquement via method="nearest")
points = [
    {'name': 'Montmorency-2020s', 'lat': 47.287816, 'lon': -71.167297},
]


def _find_coord_names(ds):
    """Detecte les noms reels des coordonnees lat/lon dans le dataset."""
    lat_name = next((c for c in ("lat", "latitude", "y") if c in ds.coords), None)
    lon_name = next((c for c in ("lon", "longitude", "x") if c in ds.coords), None)
    if lat_name is None or lon_name is None:
        raise ValueError(
            f"Coordonnees lat/lon non reconnues parmi {list(ds.coords)}."
        )
    return lat_name, lon_name


def process_point(point):
    name = point['name']
    lat_target = point['lat']
    lon_target = point['lon']

    point_dir = os.path.join(out_dir, name.replace(' ', '_'))
    os.makedirs(point_dir, exist_ok=True)

    for directory in directories:
        dir_path = os.path.join(main_dir, directory)
        point_dir_path = os.path.join(point_dir, directory)

        if not os.path.exists(dir_path):
            print(f"Dossier introuvable : {dir_path}")
            continue

        os.makedirs(point_dir_path, exist_ok=True)

        for file_name in sorted(os.listdir(dir_path)):
            if not file_name.endswith('.nc'):
                continue

            file_path = os.path.join(dir_path, file_name)
            with xr.open_dataset(file_path) as ds:
                print(f"Traitement de {file_name}")

                try:
                    lat_name, lon_name = _find_coord_names(ds)
                except ValueError as e:
                    print(f"  {e} -- fichier {file_path} ignore.")
                    continue

                # Extraction du pixel le plus proche du point demande
                ds_point = ds.sel(
                    **{lat_name: lat_target, lon_name: lon_target},
                    method="nearest",
                )

                # Rappel : le pixel effectivement selectionne (utile pour
                # verifier la distance au point demande)
                actual_lat = float(ds_point[lat_name].values)
                actual_lon = float(ds_point[lon_name].values)
                print(
                    f"  Point demande: ({lat_target}, {lon_target}) "
                    f"-> pixel le plus proche: ({actual_lat:.4f}, {actual_lon:.4f})"
                )

                output_filename = f"subset_{name.replace(' ', '_')}_{file_name}"
                output_filepath = os.path.join(point_dir_path, output_filename)
                ds_point.to_netcdf(output_filepath)
                print(f"  Sauvegarde : {output_filepath}")


if __name__ == "__main__":
    for point in points:
        process_point(point)