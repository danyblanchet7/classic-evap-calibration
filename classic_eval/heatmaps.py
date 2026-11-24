"""Heatmaps mois par mois : RMSE, R² et biais par (année, mois) + une ligne « toutes années ».

Une figure par variable (3 panneaux : RMSE | R² | Biais). Pas de temps = celui de CLASSIC
(demi-horaire, ou journalier si la sortie est journalière). Cases grises = trop peu de données.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

from . import style
from .metrics import calculate_metrics
from .prepare import align

MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def monthly_matrices(perf, min_n=15):
    """Dict {"RMSE","R2","Bias"} de DataFrames (lignes = années + 'Toutes', colonnes = mois 1..12)."""
    d = perf.dropna().copy()
    d["Y"], d["M"] = d["Date"].dt.year, d["Date"].dt.month
    years = sorted(d["Y"].unique())
    out = {k: pd.DataFrame(np.nan, index=[*years, "Toutes"], columns=range(1, 13))
           for k in ("RMSE", "R2", "Bias")}

    def fill(row, g, m):
        if len(g) >= min_n:
            r = calculate_metrics(g["OBS"], g["SIM"])
            for k in out:
                out[k].loc[row, m] = r.get(k, np.nan)

    for (y, m), g in d.groupby(["Y", "M"]):
        fill(y, g, m)
    for m, g in d.groupby("M"):
        fill("Toutes", g, m)
    return out


def _panel(ax, mat, title, cmap, norm=None, vmin=None, vmax=None):
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("#e6e6e6")
    data = np.ma.masked_invalid(mat.values.astype(float))
    im = ax.imshow(data, cmap=cm, norm=norm, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(12))
    ax.set_xticklabels(MONTHS)
    ax.set_yticks(range(len(mat)))
    ax.set_yticklabels([str(i) for i in mat.index])
    ax.axhline(len(mat) - 1.5, color="white", lw=3)           # sépare la ligne « Toutes »
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.values[i, j]
            if np.isfinite(v):
                n = float(im.norm(v))                       # texte blanc sur fond foncé
                dark = abs(n - 0.5) > 0.32 if norm is not None else n > 0.7
                ax.text(j, i, f"{v:.2g}", ha="center", va="center", fontsize=7,
                        color="white" if dark else "black")
    ax.set_title(title, loc="left", fontsize=10)
    ax.grid(False)
    plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)


def plot_heatmaps(ctx, var, out_dir):
    """Figure RMSE | R² | Biais pour une variable. Retourne (chemin, tableau long de métriques)."""
    perf = align(ctx.obs, ctx.classic[var.sim], var.obs, var.sim, resolution="native")
    if perf.empty:
        raise ValueError("aucune donnée commune")
    mats = monthly_matrices(perf, ctx.cfg.heatmap_min_n)
    fig, axes = plt.subplots(1, 3, figsize=(17, 0.55 * len(mats["RMSE"]) + 2.4))
    _panel(axes[0], mats["RMSE"], f"{var.name}: RMSE ({var.units})", "YlOrRd", vmin=0)
    _panel(axes[1], mats["R2"], f"{var.name}: R²", "YlOrRd", vmin=0, vmax=1)
    b = np.nanmax(np.abs(mats["Bias"].values)) if np.isfinite(mats["Bias"].values).any() else 1
    _panel(axes[2], mats["Bias"], f"{var.name}: Biais ({var.units}, CLASSIC - obs)", "RdBu_r",
           norm=TwoSlopeNorm(0, -b, b))
    fig.tight_layout()
    path = style.save(fig, f"{out_dir}/heatmap_{var.obs}.png")
    long = pd.concat({k: m.stack() for k, m in mats.items()}, axis=1).reset_index()
    long.columns = ["Année", "Mois", "RMSE", "R2", "Bias"]
    long.insert(0, "Variable", var.obs)
    return path, long
