# Chargement des donnees brutes (NetCDF ERA5-Land et CSV de debit)

import glob
import os

import pandas as pd
import xarray as xr


def load_point_variable_daily(folder, varname_in_file):
    """Charge tous les .nc d'un dossier (un pixel) et retourne la moyenne
    journaliere sous forme de pandas.Series."""
    nc_files = sorted(glob.glob(os.path.join(folder, "**", "*.nc"), recursive=True))
    if not nc_files:
        raise FileNotFoundError(f"Aucun fichier .nc trouve dans {folder}")

    print(f"  -> {len(nc_files)} fichier(s) trouve(s) dans {folder}")

    all_series = []
    for f in nc_files:
        ds = xr.open_dataset(f)
        if "valid_time" in ds.dims:
            ds = ds.rename({"valid_time": "time"})

        if varname_in_file not in ds.data_vars:
            raise KeyError(
                f"Variable '{varname_in_file}' absente de {f}. "
                f"Variables disponibles : {list(ds.data_vars)}"
            )

        all_series.append(ds[varname_in_file].squeeze(drop=True).to_series())
        ds.close()

    full = pd.concat(all_series, sort=False).sort_index()
    full = full[~full.index.duplicated(keep="first")]

    daily = full.resample("1D").mean()
    daily.name = varname_in_file
    return daily


def load_monthly_streamflow(csv_path):
    """Lit le CSV de debits journaliers et retourne le debit mensuel moyen."""
    df = pd.read_csv(csv_path, sep=";", decimal=".", encoding="latin1")

    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    df["Débit(m³/s)"] = pd.to_numeric(df["Débit(m³/s)"], errors="coerce")
    df = df.dropna(subset=["Date", "Débit(m³/s)"]).set_index("Date")

    return df["Débit(m³/s)"].resample("ME").mean()
