"""Analyse d'un JOUR précis : comportement de LE vs forçages météo d'entrée (étape 08).

Panneaux (axe x commun, demi-heures) : LE obs/CLASSIC, température de l'air (forçage),
rayonnement SW↓ (forçage) et, si disponible, VPD (forçage). Les forçages sont les mesures de
la tour qui pilotent CLASSIC : un écart de LE pointe donc vers la physique du modèle.
"""
import pandas as pd
import matplotlib.pyplot as plt

from . import style
from .prepare import merge_exact


def _peak_hour(s):
    t = s.idxmax()
    return t.hour + t.minute / 60


def analyze_day(ctx, day, out_dir):
    """Figure + tableau récapitulatif (moyenne, pic, heure du pic, cumul journalier de LE)."""
    cfg, c = ctx.cfg, ctx.cfg.obs_cols
    t0 = pd.Timestamp(day)
    t1 = t0 + pd.Timedelta(days=1)
    perf = merge_exact(ctx.obs[(ctx.obs["Date"] >= t0) & (ctx.obs["Date"] < t1)],
                       ctx.classic["hfls"][lambda d: (d["Date"] >= t0) & (d["Date"] < t1)],
                       c["le"], "hfls")
    if perf.empty:
        raise ValueError(f"aucune donnée LE commune obs/CLASSIC le {day}")
    forc = ctx.obs[(ctx.obs["Date"] >= t0) & (ctx.obs["Date"] < t1)].set_index("Date")

    drivers = [(c["ta_forcing"], "Température de l'air (°C)"), (c["rsd"], "SW↓ (W m-2)")]
    if c.get("vpd_forcing") in forc.columns:
        drivers.append((c["vpd_forcing"], "VPD (kPa)"))
    drivers = [(col, lab) for col, lab in drivers if col in forc.columns and forc[col].notna().any()]

    fig, axes = plt.subplots(1 + len(drivers), 1, figsize=(10, 2.8 * (1 + len(drivers))), sharex=True)
    ax = axes[0]
    style.plot_obs_sim(ax, perf["Date"], perf["OBS"], perf["SIM"], lw=1.5, marker="o", ms=3)
    ax.set_ylabel("LE (W m-2)")
    ax.legend(loc="upper left")
    ax.set_title(f"LE vs forçages d'entrée : {day}")
    for ax, (col, lab) in zip(axes[1:], drivers):
        ax.plot(forc.index, forc[col], color=style.OBS_COLOR, lw=1.5, marker="o", ms=3,
                label="Forçage (mesure tour)")
        ax.set_ylabel(lab)
    sw = forc[c["rsd"]].dropna() if c["rsd"] in forc.columns else None
    if sw is not None and len(sw):
        for a in axes:
            a.axvline(sw.idxmax(), color="gray", ls=":", lw=1)     # pic de rayonnement
    style.concise_dates(axes[-1])
    fig.tight_layout()
    fig_path = style.save(fig, f"{out_dir}/LE_day_{day}.png")

    rows = []
    for tag, col in (("Obs", "OBS"), ("CLASSIC", "SIM")):
        s = perf.set_index("Date")[col]
        rows.append({"Source": tag, "LE_moyen_Wm2": s.mean(), "LE_max_Wm2": s.max(),
                     "heure_pic_LE": _peak_hour(s), "LE_cumul_MJm2": s.mean() * 86400 / 1e6,
                     "N_demi-heures": len(s),
                     "heure_pic_SW": _peak_hour(sw) if sw is not None and len(sw) else float("nan")})
    table = pd.DataFrame(rows)
    table.to_csv(f"{out_dir}/LE_day_{day}.csv", index=False, encoding="utf-8-sig")
    return fig_path, table
