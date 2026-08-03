#!/usr/bin/env python3

import pandas as pd
import netCDF4 as nc
import numpy as np
import matplotlib.pyplot as plt
import os
from cftime import num2date


# ============================================================
# CONFIGURATION
# ============================================================

CLASSIC_PATH = (
    r"\\wsl.localhost\Ubuntu\home\classic_ops"
    r"\kyoungho_calibration\CA-MonJ"
    r"\outputFiles\Juvenile_Transient"
)

OUTPUT_PATH = (
    r"\\wsl.localhost\Ubuntu\home\classic_ops"
    r"\validation_kyoungho_results"
    r"\Juvenile_Transient"
)

OBS_PATH = "/mnt/c/Users/danyblanchet7/Desktop/"


os.makedirs(OUTPUT_PATH, exist_ok=True)


print("=" * 80)
print("VALIDATION CLASSIC - CA-MonJ - JUVENILE TRANSIENT")
print("=" * 80)

print("\nPériode CLASSIC : 2016-2024")
print(f"Répertoire CLASSIC : {CLASSIC_PATH}")
print(f"Répertoire observations : {OBS_PATH}")
print(f"Répertoire résultats : {OUTPUT_PATH}")


# ============================================================
# 1. FONCTION DE CHARGEMENT D'UNE VARIABLE CLASSIC
# ============================================================

def load_classic_variable(
    filename,
    variable_name,
    convert_flux_to_daily=False
):

    filepath = os.path.join(
        CLASSIC_PATH,
        filename
    )

    print("\n" + "-" * 70)
    print(f"Chargement CLASSIC : {filename}")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Fichier CLASSIC introuvable :\n{filepath}"
        )

    ds = nc.Dataset(filepath)

    print(
        "Variables disponibles :",
        list(ds.variables.keys())
    )

    # --------------------------------------------------------
    # Variable
    # --------------------------------------------------------

    data = ds.variables[variable_name][:]

    # --------------------------------------------------------
    # Temps
    # --------------------------------------------------------

    time = ds.variables["time"][:]

    time_units = (
        ds.variables["time"].units
    )

    calendar = getattr(
        ds.variables["time"],
        "calendar",
        "standard"
    )

    dates = num2date(
        time,
        time_units,
        calendar=calendar,
        only_use_cftime_datetimes=False
    )

    dates = pd.to_datetime(dates)

    # --------------------------------------------------------
    # Dimensions
    # --------------------------------------------------------

    print(
        "Shape originale :",
        data.shape
    )

    # Cas :
    # (time, lat, lon)

    if data.ndim == 3:

        data = data[:, 0, 0]

    # Cas :
    # (time, layer, lat, lon)

    elif data.ndim == 4:

        print(
            "⚠️ Variable multidimensionnelle "
            "(couches de sol)."
        )

        # On conserve toutes les couches
        # Cette fonction n'est donc pas adaptée
        # directement aux variables 4D.

        ds.close()

        raise ValueError(
            f"{variable_name} contient des couches : "
            f"{data.shape}. Utiliser une fonction "
            f"spécifique au sol."
        )

    # Cas :
    # (time,)

    elif data.ndim == 1:

        data = data[:]

    else:

        ds.close()

        raise ValueError(
            f"Dimension inattendue pour "
            f"{variable_name} : {data.shape}"
        )

    # --------------------------------------------------------
    # Valeurs manquantes
    # --------------------------------------------------------

    data = np.ma.filled(
        data,
        np.nan
    )

    data = data.astype(float)

    # --------------------------------------------------------
    # Conversion flux → mm/jour
    # --------------------------------------------------------

    if convert_flux_to_daily:

        data = (
            data * 86400
        )

        print(
            "Conversion appliquée : "
            "kg m-2 s-1 → mm/jour"
        )

    # --------------------------------------------------------
    # Unités
    # --------------------------------------------------------

    units = getattr(
        ds.variables[variable_name],
        "units",
        "inconnues"
    )

    print(
        "Unités originales :",
        units
    )

    # --------------------------------------------------------
    # Série temporelle
    # --------------------------------------------------------

    series = pd.Series(
        data,
        index=dates,
        name=variable_name
    )

    print(
        "Nombre de valeurs :",
        len(series)
    )

    print(
        "Période :",
        series.index.min(),
        "→",
        series.index.max()
    )

    print(
        "Valeurs min/max :",
        np.nanmin(data),
        "/",
        np.nanmax(data)
    )

    ds.close()

    return series


# ============================================================
# 2. CHARGER LES SORTIES CLASSIC
# ============================================================

print("\n" + "=" * 80)
print("CHARGEMENT DES SORTIES CLASSIC")
print("=" * 80)


# ------------------------------------------------------------
# Transpiration
# ------------------------------------------------------------

TRAN_CLASSIC = load_classic_variable(
    "tran_daily.nc",
    "tran",
    convert_flux_to_daily=True
)


# ------------------------------------------------------------
# Évapotranspiration totale
# ------------------------------------------------------------

ET_CLASSIC = load_classic_variable(
    "evspsbl_daily.nc",
    "evspsbl",
    convert_flux_to_daily=True
)


# ------------------------------------------------------------
# Évaporation du sol
# ------------------------------------------------------------

E_SOIL_CLASSIC = load_classic_variable(
    "evspsblsoi_daily.nc",
    "evspsblsoi",
    convert_flux_to_daily=True
)


# ------------------------------------------------------------
# Évaporation du couvert
# ------------------------------------------------------------

E_VEG_CLASSIC = load_classic_variable(
    "evspsblveg_daily.nc",
    "evspsblveg",
    convert_flux_to_daily=True
)


# ============================================================
# 3. CONSTRUIRE UN DATAFRAME CLASSIC
# ============================================================

classic = pd.concat(
    [
        TRAN_CLASSIC.rename("TRAN_CLASSIC"),
        ET_CLASSIC.rename("ET_CLASSIC"),
        E_SOIL_CLASSIC.rename("E_SOIL_CLASSIC"),
        E_VEG_CLASSIC.rename("E_VEG_CLASSIC")
    ],
    axis=1
)

print("\n" + "=" * 80)
print("RÉSUMÉ DES SORTIES CLASSIC")
print("=" * 80)

print(classic.head())

print("\nStatistiques :")

print(
    classic.describe()
)


# ============================================================
# 4. SAUVEGARDER LES SORTIES CLASSIC EN CSV
# ============================================================

classic_csv = os.path.join(
    OUTPUT_PATH,
    "CLASSIC_Juvenile_Transient_daily.csv"
)

classic.to_csv(
    classic_csv
)

print(
    "\n✓ Sorties CLASSIC sauvegardées :"
)

print(
    classic_csv
)


# ============================================================
# 5. PLOT DES VARIABLES CLASSIC
# ============================================================

print("\n" + "=" * 80)
print("CRÉATION DES FIGURES")
print("=" * 80)


# ------------------------------------------------------------
# Transpiration
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(14, 6)
)

ax.plot(
    classic.index,
    classic["TRAN_CLASSIC"],
    linewidth=1
)

ax.set_title(
    "CLASSIC - Transpiration - CA-MonJ\n"
    "Juvenile Transient 2016-2024"
)

ax.set_xlabel(
    "Date"
)

ax.set_ylabel(
    "Transpiration (mm/jour)"
)

ax.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

output_file = os.path.join(
    OUTPUT_PATH,
    "CLASSIC_Transpiration_2016_2024.png"
)

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ------------------------------------------------------------
# Évapotranspiration
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(14, 6)
)

ax.plot(
    classic.index,
    classic["ET_CLASSIC"],
    linewidth=1
)

ax.set_title(
    "CLASSIC - Évapotranspiration\n"
    "CA-MonJ - Juvenile Transient 2016-2024"
)

ax.set_xlabel(
    "Date"
)

ax.set_ylabel(
    "ET (mm/jour)"
)

ax.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

output_file = os.path.join(
    OUTPUT_PATH,
    "CLASSIC_ET_2016_2024.png"
)

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ============================================================
# 6. CHARGER L'HUMIDITÉ DU SOL
# ============================================================

def load_soil_moisture(
    filename,
    variable_name
):

    filepath = os.path.join(
        CLASSIC_PATH,
        filename
    )

    print("\n" + "-" * 70)
    print(
        "Chargement humidité du sol :",
        filename
    )

    ds = nc.Dataset(filepath)

    data = ds.variables[
        variable_name
    ][:]

    time = ds.variables[
        "time"
    ][:]

    time_units = ds.variables[
        "time"
    ].units

    calendar = getattr(
        ds.variables["time"],
        "calendar",
        "standard"
    )

    dates = num2date(
        time,
        time_units,
        calendar=calendar,
        only_use_cftime_datetimes=False
    )

    dates = pd.to_datetime(
        dates
    )

    print(
        "Shape :",
        data.shape
    )

    # --------------------------------------------------------
    # Shape attendue :
    #
    # (time, layer, lat, lon)
    # --------------------------------------------------------

    if data.ndim != 4:

        ds.close()

        raise ValueError(
            "La structure de mrsol n'est pas "
            f"celle attendue : {data.shape}"
        )

    # Extraire le point CA-MonJ
    #
    # Résultat :
    # (time, layer)

    data = data[
        :,
        :,
        0,
        0
    ]

    data = np.ma.filled(
        data,
        np.nan
    )

    data = data.astype(float)

    ds.close()

    return dates, data


soil_dates, soil_data = load_soil_moisture(
    "mrsol_daily.nc",
    "mrsol"
)


# ============================================================
# 7. CALCULER L'HUMIDITÉ TOTALE DU SOL
# ============================================================

# Somme des 20 couches
#
# Attention :
# cette quantité correspond à la somme de la masse
# d'eau contenue dans les couches et non directement
# à une teneur volumique.

soil_total = np.nansum(
    soil_data,
    axis=1
)

soil_series = pd.Series(
    soil_total,
    index=soil_dates,
    name="MRsol_total"
)


# ============================================================
# 8. PLOT HUMIDITÉ DU SOL
# ============================================================

fig, ax = plt.subplots(
    figsize=(14, 6)
)

ax.plot(
    soil_series.index,
    soil_series.values,
    linewidth=1
)

ax.set_title(
    "CLASSIC - Stock total d'eau dans le sol\n"
    "CA-MonJ - Juvenile Transient 2016-2024"
)

ax.set_xlabel(
    "Date"
)

ax.set_ylabel(
    "Stock d'eau du sol (kg m$^{-2}$)"
)

ax.grid(
    True,
    alpha=0.3
)

plt.tight_layout()

output_file = os.path.join(
    OUTPUT_PATH,
    "CLASSIC_SoilWater_2016_2024.png"
)

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()


# ============================================================
# 9. SAUVEGARDER L'HUMIDITÉ DU SOL
# ============================================================

soil_df = pd.DataFrame(
    {
        "MRsol_total": soil_series
    }
)

soil_csv = os.path.join(
    OUTPUT_PATH,
    "CLASSIC_SoilWater_2016_2024.csv"
)

soil_df.to_csv(
    soil_csv
)


print(
    "\n✓ Humidité du sol sauvegardée :"
)

print(
    soil_csv
)


# ============================================================
# 10. RÉSUMÉ FINAL
# ============================================================

print("\n" + "=" * 80)
print("ANALYSE TERMINÉE")
print("=" * 80)

print(
    "\nVariables CLASSIC analysées :"
)

print(
    "  ✓ Transpiration"
)

print(
    "  ✓ Évapotranspiration totale"
)

print(
    "  ✓ Évaporation du sol"
)

print(
    "  ✓ Évaporation du couvert"
)

print(
    "  ✓ Stock d'eau du sol"
)

print(
    "\nRésultats disponibles dans :"
)

print(
    OUTPUT_PATH
)

print(
    "\nÉtape suivante : comparaison avec les observations."
)

print("=" * 80)