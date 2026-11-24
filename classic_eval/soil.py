#Sorties CLASSIC sans équivalent observé : eau du sol par couche, profondeur racinaire.
import os
import netCDF4 as nc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from . import style
from .loaders import read_time


def plot_soil_water_layers(classic_dir, output_path, year, filename="mrsol_daily.nc"):
    """Eau du sol simulée (mrsol, kg m-2) pour l'année `year` : couche 0 SEULE (figure 1),
    toutes les autres couches sur le MÊME graphique (figure 2, nuances de bleu)."""
    ds = nc.Dataset(os.path.join(classic_dir, filename))
    try:
        raw = ds.variables["mrsol"]                       # (time, layer, lat, lon)
        dates = read_time(ds)
        series = []
        for layer in range(raw.shape[1]):
            s = pd.Series(raw[:, layer, 0, 0].astype(float).filled(float("nan")), index=dates)
            series.append(s[s.index.year == year])
    finally:
        ds.close()
    files = []
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(series[0].index, series[0].values, color=style.SIM_COLOR, lw=1.5)
    ax.set_ylabel("mrsol (kg/m²)")
    ax.set_title(f"CLASSIC - Eau du sol - Couche 0 - {year}")
    style.concise_dates(ax)
    fig.tight_layout()
    files.append(style.save(fig, os.path.join(output_path, f"mrsol_layer0_{year}.png")))

    if len(series) > 1:
        fig, ax = plt.subplots(figsize=(10, 5))
        shades = plt.get_cmap("Blues")(np.linspace(0.9, 0.35, len(series) - 1))
        for layer, c in zip(range(1, len(series)), shades):
            ax.plot(series[layer].index, series[layer].values, color=c, lw=1.5, label=f"Couche {layer}")
        ax.set_ylabel("mrsol (kg/m²)")
        ax.set_title(f"CLASSIC - Eau du sol - Couches 1 à {len(series) - 1} - {year}")
        ax.legend(ncol=2)
        style.concise_dates(ax)
        fig.tight_layout()
        files.append(style.save(fig, os.path.join(output_path, f"mrsol_layers_1_to_{len(series) - 1}_{year}.png")))
    return files


def plot_root_depth(root_df, output_path, start_year, end_year):
    """Profondeur racinaire (m) par PFT (colonnes de root_df hors `Date`), traits bleus."""
    d = root_df[(root_df["Date"].dt.year >= start_year) & (root_df["Date"].dt.year <= end_year)]
    fig, ax = plt.subplots(figsize=(12, 5))
    for ls, col in zip(("-", "--", ":", "-."), [c for c in d.columns if c != "Date"]):
        ax.plot(d["Date"], d[col], color=style.SIM_COLOR, ls=ls, marker="o", ms=3, lw=1.5, label=col)
    ax.set_ylabel("Profondeur racinaire (m)")
    ax.set_title(f"CLASSIC - Profondeur racinaire - {start_year}-{end_year}")
    ax.legend()
    style.concise_dates(ax)
    fig.tight_layout()
    return style.save(fig, os.path.join(output_path, f"root_depth_{start_year}_{end_year}.png"))
