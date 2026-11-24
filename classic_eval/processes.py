"""Processus : pourquoi l'erreur se produit-elle ?

- albédo selon l'état de la neige
- réponse de GPP / LE / H aux forçages (TA, SW, VPD) : courbes binnées obs vs sim
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from . import style


#  ALBÉDO
def _midday_albedo(df, up, down, rsd_min=100, hours=(10, 14)):
    d = df[["Date", up, down]].dropna().copy()
    h = d["Date"].dt.hour
    d = d[(h >= hours[0]) & (h <= hours[1]) & (d[down] > rsd_min)]
    d["alb"] = d[up] / d[down]
    d = d[(d["alb"] > 0) & (d["alb"] < 1)]
    return d.set_index("Date")["alb"].resample("1D").median().dropna()


def albedo_vs_snow(obs, classic, obs_cols, output_path,
                   bins=(0, 0.01, 0.1, 0.3, np.inf),
                   labels=("sans neige", "mince <10cm", "moyenne 10-30cm", "épaisse >30cm")):
    """Albédo journalier de midi (obs vs CLASSIC) par classe de hauteur de neige (snd simulé).

    obs_cols : cfg.obs_cols (colonnes rsu / rsd). Retourne (tableau médianes/biais, données).
    """
    a_obs = _midday_albedo(obs, obs_cols["rsu"], obs_cols["rsd"])
    sim = classic["rsds"].merge(classic["rsus"], on="Date")
    a_sim = _midday_albedo(sim, "rsus", "rsds")
    snow = classic["snd"].set_index("Date")["snd"].resample("1D").mean()
    snow.index = pd.to_datetime(snow.index).normalize()

    d = pd.concat({"OBS": a_obs, "SIM": a_sim, "snd": snow}, axis=1).dropna()
    d["classe"] = pd.cut(d["snd"], bins=list(bins), labels=list(labels), right=False)
    t = d.groupby("classe", observed=True).agg(
        n=("OBS", "size"), obs_med=("OBS", "median"), sim_med=("SIM", "median"))
    t["biais"] = t["sim_med"] - t["obs_med"]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, cl in enumerate(t.index):
        sub = d[d["classe"] == cl]
        if sub.empty:
            continue
        for pos, col, color in ((i - 0.18, "OBS", style.OBS_COLOR), (i + 0.18, "SIM", style.SIM_COLOR)):
            b = ax.boxplot(sub[col], positions=[pos], widths=0.3, patch_artist=True,
                           boxprops=dict(edgecolor=color), medianprops=dict(color=color),
                           whiskerprops=dict(color=color), capprops=dict(color=color),
                           flierprops=dict(markeredgecolor=color, markersize=3))
            b["boxes"][0].set_facecolor("white")
    ax.set_xticks(range(len(t)))
    ax.set_xticklabels([f"{c}\n(n={n})" for c, n in zip(t.index, t["n"])])
    ax.set_ylabel("Albédo (midi)")
    ax.set_title("Albédo vs état de la neige  (gris = obs, bleu = CLASSIC)")
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, "albedo_vs_snow.png"))
    return t, d


# RÉPONSE AUX FORÇAGES
def binned_response(obs, classic, flux_obs, flux_sim, driver_obs, driver_label, flux_label,
                    output_path, nbins=12, daytime_col="Rsd_J", daytime_min=20, months=range(5, 10)):
    """Flux (obs vs sim) en fonction d'un forçage observé, par classes de quantiles.

    Les forçages sont ceux mesurés à la tour (aussi utilisés pour piloter CLASSIC), donc un
    écart de réponse pointe vers la physique du modèle, pas le forçage.
    Jour seulement (daytime_col > daytime_min) et mois `months`. Retourne le tableau binné.
    """
    cols = list(dict.fromkeys(["Date", flux_obs, driver_obs, daytime_col]))
    o = obs[cols].dropna()
    s = classic[flux_sim][["Date", flux_sim]].rename(columns={flux_sim: "SIM"})
    d = o.merge(s, on="Date").dropna()
    d = d[(d[daytime_col] > daytime_min) & d["Date"].dt.month.isin(list(months))]
    if len(d) < nbins * 5:
        raise ValueError(f"Pas assez de points ({len(d)}) pour {flux_label} vs {driver_label}")
    d["bin"] = pd.qcut(d[driver_obs], nbins, duplicates="drop")
    g = d.groupby("bin", observed=True)
    t = pd.DataFrame({
        "driver": g[driver_obs].median(),
        "obs_med": g[flux_obs].median(),
        "obs_q25": g[flux_obs].quantile(0.25), "obs_q75": g[flux_obs].quantile(0.75),
        "sim_med": g["SIM"].median(),
        "sim_q25": g["SIM"].quantile(0.25), "sim_q75": g["SIM"].quantile(0.75),
        "n": g.size(),
    })
    t["biais"] = t["sim_med"] - t["obs_med"]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(t["driver"], t["obs_med"], "o-", color=style.OBS_COLOR, label=style.OBS_LABEL)
    ax.fill_between(t["driver"], t["obs_q25"], t["obs_q75"], color=style.OBS_COLOR, alpha=0.15)
    ax.plot(t["driver"], t["sim_med"], "s-", color=style.SIM_COLOR, label=style.SIM_LABEL)
    ax.fill_between(t["driver"], t["sim_q25"], t["sim_q75"], color=style.SIM_COLOR, alpha=0.15)
    ax.set_xlabel(driver_label)
    ax.set_ylabel(flux_label)
    ax.set_title(f"{flux_label} vs {driver_label} (médiane, IQR)")
    ax.legend()
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, f"response_{flux_obs}_vs_{driver_obs}.png"))
    return t.reset_index(drop=True)
