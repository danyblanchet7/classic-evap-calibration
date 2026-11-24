"""Évapotranspiration : ET observée (ET_J_ful) vs ET totale CLASSIC et ses composantes.

CLASSIC : evspsbl (total), evspsblsoi (évaporation du sol), evspsblveg (végétation, interception
comprise). Les observations ne séparent pas les composantes : elles se comparent au total.
Figure : cycle annuel moyen (gauche) et année d'exemple en moyennes journalières (droite).
"""
import pandas as pd
import matplotlib.pyplot as plt

from . import style
from .prepare import daily_mean


def _lines(ax, d, x):
    ax.plot(x, d["OBS"], color=style.OBS_COLOR, lw=1.6, label="ET obs (total)")
    ax.plot(x, d["SIM"], color=style.SIM_COLOR, lw=1.6, label="CLASSIC total")
    ax.plot(x, d["SOL"], color=style.SIM_COLOR, lw=1.1, ls="--", label="CLASSIC sol")
    ax.plot(x, d["VEG"], color=style.SIM_COLOR, lw=1.1, ls=":", label="CLASSIC végétation")


def plot_et_partition(ctx, var, year, out_dir):
    """Retourne (chemin de la figure, tableau moyen mensuel mm/j)."""
    for k in ("et_soi_mmd", "et_veg_mmd"):
        if k not in ctx.classic:
            raise KeyError(f"{k} absent : ajouter evspsblsoi / evspsblveg dans cfg.classic_files")
    d = ctx.daily_perf(var).set_index("Date")
    d["SOL"] = daily_mean(ctx.classic["et_soi_mmd"], "et_soi_mmd")
    d["VEG"] = daily_mean(ctx.classic["et_veg_mmd"], "et_veg_mmd")
    d = d.dropna()
    monthly = d.resample("MS").mean().dropna()
    clim = monthly.groupby(monthly.index.month).mean()
    clim["fraction_sol"] = clim["SOL"] / clim["SIM"]
    clim["fraction_veg"] = clim["VEG"] / clim["SIM"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 4.8))
    _lines(a1, clim, clim.index)
    a1.set_xticks(range(1, 13))
    a1.set_xticklabels(list("JFMAMJJASOND"))
    a1.set_ylabel("ET (mm/j)")
    a1.set_title("Cycle annuel moyen")
    a1.legend()
    y = d[d.index.year == year]
    if len(y):
        _lines(a2, y, y.index)
        style.concise_dates(a2)
    a2.set_title(f"Année {year} (moyennes journalières)")
    fig.suptitle("Évapotranspiration : observée vs CLASSIC (total, sol, végétation)")
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/ET_partition.png"), clim
