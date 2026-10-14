# -*- coding: utf-8 -*-
"""Tous les graphiques. Chaque fonction sauvegarde un PNG dans output_dir."""

import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde, norm

from standardization import empirical_probability, reference_values

QUAD_LIM = 3.0


def _save(fig, cfg, filename, **kwargs):
    path = os.path.join(cfg["output_dir"], filename)
    fig.savefig(path, dpi=150, **kwargs)
    plt.close(fig)
    print(f"  - {os.path.abspath(path)}")


def _quadrant_background(ax, df):
    """Densite KDE (verte) + lignes a 0 + labels des 4 cadrans."""
    grid = np.linspace(-QUAD_LIM, QUAD_LIM, 200)
    xx, yy = np.meshgrid(grid, grid)
    positions = np.vstack([xx.ravel(), yy.ravel()])

    kde = gaussian_kde(np.vstack([df["SSMI"].values, df["SAMI"].values]))
    ax.contourf(xx, yy, np.reshape(kde(positions).T, xx.shape), levels=12, cmap="Greens")

    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)

    pad = 0.05 * QUAD_LIM
    ax.text(-QUAD_LIM + pad, QUAD_LIM - pad, "Wet air, dry soil", ha="left", va="top", fontsize=9)
    ax.text(QUAD_LIM - pad, QUAD_LIM - pad, "Wet air, wet soil", ha="right", va="top", fontsize=9)
    ax.text(-QUAD_LIM + pad, -QUAD_LIM + pad, "Dry air, dry soil", ha="left", va="bottom", fontsize=9)
    ax.text(QUAD_LIM - pad, -QUAD_LIM + pad, "Dry air, wet soil", ha="right", va="bottom", fontsize=9)

    ax.set_xlim(-QUAD_LIM, QUAD_LIM)
    ax.set_ylim(-QUAD_LIM, QUAD_LIM)
    ax.set_xlabel("SSMI (-)")
    ax.set_ylabel("SAMI (-)")
    return xx, yy, positions


def plot_vpd_reference_period(vpd, cfg):
    ref_start, ref_end = pd.Timestamp(cfg["ref_period"][0]), pd.Timestamp(cfg["ref_period"][1])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(vpd.index, vpd.values, linewidth=0.7, label="VPD")
    ref = vpd.loc[ref_start:ref_end]
    ax.plot(ref.index, ref.values, linewidth=0.8, label="VPD - période de référence")
    ax.axvspan(ref_start, ref_end, alpha=0.15, label="Période de référence")
    ax.set_ylabel("VPD (kPa)")
    ax.set_xlabel("Date")
    ax.set_title("VPD et période de référence")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, cfg, "VPD_reference_period.png")


def plot_indices_reference_period(sami, ssmi, cfg):
    ref_start, ref_end = pd.Timestamp(cfg["ref_period"][0]), pd.Timestamp(cfg["ref_period"][1])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(sami.loc[ref_start:ref_end], linewidth=0.7, label="SAMI")
    ax.plot(ssmi.loc[ref_start:ref_end], linewidth=0.7, label="SSMI")
    for thr in (-0.5, -1.0, -1.5, -2.0):
        ax.axhline(thr, linestyle="--", linewidth=0.8)
    ax.axhline(0, linewidth=0.8)
    ax.set_xlabel("Date")
    ax.set_ylabel("Indice standardisé")
    ax.set_title(f"SAMI et SSMI pendant la période de référence "
                 f"({ref_start.date()} - {ref_end.date()})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, cfg, "SAMI_SSMI_reference_period.png")


def plot_quadrant_density(sami, ssmi, cfg):
    """Densite SAMI vs SSMI (4 cadrans), contours bleus pour les annees en surbrillance."""
    highlight_years = cfg.get("quadrant_highlight_years")
    df = pd.concat([ssmi.rename("SSMI"), sami.rename("SAMI")], axis=1).dropna()
    if len(df) < 10:
        print("  ! Pas assez de points valides pour le graphique en 4 cadrans.")
        return

    fig, ax = plt.subplots(figsize=(7, 6.5))
    xx, yy, positions = _quadrant_background(ax, df)

    if highlight_years:
        hl = df[df.index.year.isin(highlight_years)]
        if len(hl) >= 10:
            kde_hl = gaussian_kde(np.vstack([hl["SSMI"].values, hl["SAMI"].values]))
            ax.contour(xx, yy, np.reshape(kde_hl(positions).T, xx.shape),
                       levels=8, cmap="Blues", linewidths=1.2)
        else:
            print(f"  ! Pas assez de points pour {highlight_years} ({len(hl)}).")

    title = "Densité SAMI vs SSMI (saison de croissance)"
    if highlight_years:
        title += f" - contours bleus : {highlight_years}"
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    _save(fig, cfg, "SAMI_SSMI_quadrants.png")


def plot_quadrant_events(sami, ssmi, events_df, cfg):
    """Trajectoires jour par jour des episodes les plus severes sur la carte 2D."""
    if events_df.empty:
        print("  ! Aucun episode a tracer.")
        return

    df = pd.concat([ssmi.rename("SSMI"), sami.rename("SAMI")], axis=1).dropna()
    top_events = events_df.head(cfg["event_top_n_to_plot"])
    colors = plt.cm.plasma(np.linspace(0.1, 0.85, len(top_events)))

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    _quadrant_background(ax, df)

    for (_, ev), color in zip(top_events.iterrows(), colors):
        traj = df.loc[pd.Timestamp(ev["start"]):pd.Timestamp(ev["end"])]
        if traj.empty:
            continue
        ax.plot(traj["SSMI"], traj["SAMI"], color=color, linewidth=1.6, marker="o",
                markersize=2.5, zorder=5,
                label=f"{ev['start']} -> {ev['end']} ({ev['duration_days']} j)")
        ax.plot(traj["SSMI"].iloc[0], traj["SAMI"].iloc[0], marker="^", color=color, markersize=8, zorder=6)
        ax.plot(traj["SSMI"].iloc[-1], traj["SAMI"].iloc[-1], marker="s", color=color, markersize=7, zorder=6)

    ax.set_title(f"Trajectoires des {len(top_events)} épisodes secs les plus sévères\n"
                 "(triangle = début, carré = fin)", fontsize=11)
    ax.legend(loc="lower right", fontsize=7, framealpha=0.9)
    fig.tight_layout()
    _save(fig, cfg, "SAMI_SSMI_quadrants_events.png")


def plot_indices_comparison(sami, ssmi, ssi3, cfg):
    """SAMI, SSMI et SSI-3 sur la periode cfg['display_period']."""
    start, end = pd.Timestamp(cfg["display_period"][0]), pd.Timestamp(cfg["display_period"][1])

    fig, ax = plt.subplots(figsize=(16, 6))
    fig.suptitle(f"Comparaison des indices de sécheresse – Montmorency "
                 f"({start.date()} – {end.date()})", fontsize=14, fontweight="bold")

    ax.plot(sami.loc[start:end], linewidth=0.8, label="SAMI – atmosphère")
    ax.plot(ssmi.loc[start:end], linewidth=0.8, label="SSMI – sol")
    ax.plot(ssi3.loc[start:end], linewidth=0.9, label="SSI-3 – débit")

    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.axhline(-1, color="orange", linestyle="--", linewidth=0.8, label="Modérée (−1)")
    ax.axhline(-1.5, color="red", linestyle="--", linewidth=0.8, label="Sévère (−1.5)")
    ax.axhline(-2, color="darkred", linestyle="--", linewidth=0.8, label="Extrême (−2)")

    ax.set_ylabel("Indice standardisé")
    ax.set_ylim(-3.5, 3.5)
    ax.set_xlabel("Date")

    # Graduation adaptee a la longueur de la periode affichee
    if (end - start).days > 730:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    _save(fig, cfg, "SAMI_SSMI_SSI3_comparison.png", bbox_inches="tight")


def plot_lagged_correlation(prop_df, lag_col, title, filename, cfg):
    """Correlation croisee en fonction du decalage (jours ou mois)."""
    valid = prop_df.dropna(subset=["correlation"])
    if valid.empty:
        print(f"  ! Aucune correlation valide pour {filename}.")
        return

    best = prop_df.loc[valid["correlation"].idxmax()]
    unit = "j" if lag_col == "lag_days" else "mois"
    xlabel = "Décalage temporel (jours)" if lag_col == "lag_days" else "Décalage temporel (mois)"

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(prop_df[lag_col], prop_df["correlation"], marker="o", markersize=3, linewidth=1.2)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.axvline(0, color="black", linestyle="--", linewidth=0.8)
    ax.scatter(best[lag_col], best["correlation"], color="red", zorder=5,
               label=f"Maximum : lag = {best[lag_col]:.0f} {unit}, r = {best['correlation']:.2f}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Corrélation de Pearson (r)")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, cfg, filename, bbox_inches="tight")


def plot_empirical_cdf(vpd, soil, cfg):
    """CDF empirique utilisee pour la standardisation (VPD et humidite du sol).

    Ligne du haut : p = F(valeur), avec la formule (k + 1) / (n_ref + 2).
    Ligne du bas  : z = norm.ppf(p), c'est-a-dire la valeur de l'indice.
    NB : SSMI = z directement ; SAMI = -z (signe inverse pour le VPD).
    """
    panels = [
        (vpd, "VPD", "kPa"),
        (soil, "Humidité du sol", "m³/m³"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    season = cfg["growing_season_months"]

    for col, (series, label, unit) in enumerate(panels):
        ref = reference_values(series, cfg["ref_period"], season)
        prob = empirical_probability(ref, ref)
        z = norm.ppf(prob)
        median = np.median(ref)

        ax = axes[0, col]
        ax.step(ref, prob, where="post", linewidth=1.3)
        ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
        ax.axvline(median, color="gray", linestyle=":", linewidth=0.8)
        ax.set_ylim(0, 1)
        ax.set_ylabel("Probabilité cumulée p")
        ax.set_title(f"CDF empirique – {label}\n"
                     f"(n = {len(ref)} jours, mois {season[0]}–{season[1]}, "
                     f"{cfg['ref_period'][0][:4]}–{cfg['ref_period'][1][:4]})", fontsize=10)
        ax.grid(alpha=0.3)

        ax = axes[1, col]
        ax.plot(ref, z, linewidth=1.3)
        ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
        for thr in (-2, -1, 1, 2):
            ax.axhline(thr, color="gray", linestyle=":", linewidth=0.8)
        ax.set_xlabel(f"{label} ({unit})")
        ax.set_ylabel("z = Φ⁻¹(p)")
        ax.set_title("Transformation en score normalisé"
                     + (" (SAMI = −z)" if label == "VPD" else " (SSMI = z)"), fontsize=10)
        ax.grid(alpha=0.3)

    fig.tight_layout()
    _save(fig, cfg, "empirical_CDF_VPD_soil.png")


def plot_distributions_and_cdf(vpd, soil, cfg):
    """Distribution + CDF empirique, puis comparaison avec la loi normale.

    Ligne du haut : histogramme des valeurs de reference (axe gauche) et
                    CDF empirique (axe droit).
    Ligne du bas  : cloche N(0,1) + histogramme des scores obtenus (axe
                    gauche) ; CDF empirique des scores vs CDF normale (axe droit).
    Scores : SAMI = -z pour le VPD, SSMI = +z pour l'humidite du sol.
    """
    panels = [
        (vpd, "VPD", "kPa", -1, "SAMI"),
        (soil, "Humidité du sol", "m³/m³", +1, "SSMI"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    season = cfg["growing_season_months"]
    x_norm = np.linspace(-4, 4, 400)

    for col, (series, label, unit, sign, idx_name) in enumerate(panels):
        ref = reference_values(series, cfg["ref_period"], season)
        n = len(ref)
        prob = empirical_probability(ref, ref)
        z = sign * norm.ppf(prob)

        # ---------- Ligne 1 : histogramme + CDF empirique ----------
        ax = axes[0, col]
        h = ax.hist(ref, bins=40, color="#9ecae1", edgecolor="white", label="Histogramme")
        ax.set_xlabel(f"{label} ({unit})")
        ax.set_ylabel("Nombre de jours")
        ax.set_title(f"{label} – distribution et CDF empirique (n = {n})", fontsize=10)

        ax_r = ax.twinx()
        l_cdf, = ax_r.step(ref, prob, where="post", color="C3", linewidth=1.5,
                           label="CDF empirique")
        ax_r.set_ylim(0, 1)
        ax_r.set_ylabel("Probabilité cumulée p")
        ax.legend([h[2][0], l_cdf], ["Histogramme", "CDF empirique"], loc="center right", fontsize=8)
        ax.grid(alpha=0.3)

        # ---------- Ligne 2 : cloche N(0,1) + z + CDF ----------
        ax = axes[1, col]
        h = ax.hist(z, bins=40, density=True, color="#a1d99b", edgecolor="white")
        l_pdf, = ax.plot(x_norm, norm.pdf(x_norm), color="black", linewidth=1.8)
        ax.set_xlim(-4, 4)
        ax.set_xlabel(f"{idx_name} (écart-type)")
        ax.set_ylabel("Densité")
        ax.set_title(f"{idx_name} - scores obtenus vs loi normale N(0,1)", fontsize=10)

        z_sorted = np.sort(z)
        ax_r = ax.twinx()
        l_ecdf, = ax_r.step(z_sorted, np.arange(1, n + 1) / n, where="post",
                            color="C3", linewidth=1.5)
        ax_r.set_ylim(0, 1)
        ax_r.set_ylabel("Probabilité cumulée")
        ax.legend([h[2][0], l_pdf, l_ecdf],
                  [f"Histogramme de {idx_name}", "Densité N(0,1)",
                   "CDF empirique"],
                  loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)

    fig.tight_layout()
    _save(fig, cfg, "distributions_CDF_normale.png")
