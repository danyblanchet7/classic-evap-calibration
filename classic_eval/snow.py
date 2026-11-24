##Neige et albédo (étape 04) : obs vs CLASSIC quand des obs existent, sinon CLASSIC seul (bleu).
import os
import pandas as pd
import matplotlib.pyplot as plt
from . import style
from .temporal import load_obs_snow_sites


def plot_snow_depth_comparison(obs_csv, classic, output_path, sites=("LG", "CAN"),
                               window=("2023-10-01", "2025-06-01")):
    """Hauteur de neige (cm) : chaque site obs (gris), moyenne des sites (gris foncé), CLASSIC (bleu)."""
    obs = load_obs_snow_sites(obs_csv, sites, window[0], pd.Timestamp(window[1]) - pd.Timedelta(days=1))
    snd = classic["snd"].set_index("Date")["snd"].resample("1D").mean() * 100
    snd = snd[(snd.index >= window[0]) & (snd.index < window[1])]
    fig, ax = plt.subplots(figsize=(14, 6))
    for i, s in enumerate(sites):
        ax.plot(obs.index, obs[s], color=style.OBS_GREYS[i % len(style.OBS_GREYS)], lw=1,
                label=f"Obs site {s}")
    ax.plot(obs.index, obs["mean"], color=style.OBS_COLOR, lw=2, label=f"Obs moyenne {'+'.join(sites)}")
    ax.plot(snd.index, snd, color=style.SIM_COLOR, lw=1.2, label=style.SIM_LABEL)
    ax.set_xlabel("Date")
    ax.set_ylabel("Hauteur de neige (cm)")
    ax.legend()
    style.concise_dates(ax)
    fig.tight_layout()
    return style.save(fig, os.path.join(output_path, "snow_depth_obs_vs_classic.png"))


def plot_snow_variables(classic, snow_variables, output_path):
    """Variables de neige simulées (SWE, couverture, fonte, hauteur), toutes années."""
    names = [v for v in snow_variables if v in classic]
    fig, axes = plt.subplots(len(names), 1, figsize=(12, 3 * len(names)), sharex=True, squeeze=False)
    for ax, var in zip(axes.ravel(), names):
        df = classic[var]
        ax.plot(df["Date"], df[var], color=style.SIM_COLOR, lw=1)
        ax.set_ylabel(snow_variables[var])
        ax.set_title(f"CLASSIC - {var}", fontsize=9)
    style.concise_dates(axes.ravel()[-1])
    fig.tight_layout()
    return style.save(fig, os.path.join(output_path, "snow_variables_simulated.png"))


def plot_albedo_evolution(classic, output_path):
    """Albédo de surface simulé (bleu) et couverture de neige (vert, axe de droite)."""
    albedo = classic["albs"].set_index("Date")["albs"].resample("1D").mean()
    cover = classic["snc"].set_index("Date")["snc"].resample("1D").mean()
    df = pd.concat([albedo.rename("Albedo"), cover.rename("Snow cover")], axis=1)

    fig, ax1 = plt.subplots(figsize=(14, 5))
    ax1.plot(df.index, df["Albedo"], color=style.SIM_COLOR, lw=1.2, label="Albédo de surface (CLASSIC)")
    ax1.set_ylabel("Albédo (-)")
    ax1.set_ylim(bottom=0)
    ax2 = ax1.twinx()
    ax2.plot(df.index, df["Snow cover"], color="tab:green", lw=1, alpha=0.65, label="Couverture neigeuse")
    ax2.set_ylabel("Fraction de couverture neigeuse (-)", color="tab:green")
    ax2.set_ylim(0, 1)
    ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")
    ax1.set_title("Évolution de l'albédo et de la couverture neigeuse")
    style.concise_dates(ax1)
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, "albedo_evolution.png"), dpi=200)
    return df
