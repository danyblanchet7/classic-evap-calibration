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

def _save(fig, cfg, filename, dpi=150, **kwargs):
    path = os.path.join(cfg["output_dir"], filename)
    fig.savefig(path, dpi=dpi, **kwargs)
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
    """Densite SAMI vs SSMI avec deux distributions marginales."""

    highlight_years = cfg.get("quadrant_highlight_years")

    df = pd.concat(
        [ssmi.rename("SSMI"), sami.rename("SAMI")],
        axis=1
    ).dropna()

    if len(df) < 10:
        print("  ! Pas assez de points valides pour le graphique en 4 cadrans.")
        return

    # Annees en surbrillance
    hl = df[df.index.year.isin(highlight_years)] if highlight_years else None

    # ---------------------------------------------------------
    # Figure : marginale du haut, graphique central, marginale droite
    # ---------------------------------------------------------
    fig = plt.figure(figsize=(8, 7.2))

    gs = fig.add_gridspec(
        2, 2,
        width_ratios=[5, 1.15],
        height_ratios=[1.15, 5],
        left=0.12,
        right=0.96,
        bottom=0.11,
        top=0.90,
        wspace=0.04,
        hspace=0.04
    )

    ax_top = fig.add_subplot(gs[0, 0])
    ax = fig.add_subplot(gs[1, 0], sharex=ax_top)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax)

    # ---------------------------------------------------------
    # 1. GRAPHIQUE CENTRAL : code original conservé
    # ---------------------------------------------------------
    xx, yy, positions = _quadrant_background(ax, df)

    if highlight_years:
        if len(hl) >= 10:
            kde_hl = gaussian_kde(
                np.vstack([hl["SSMI"].values, hl["SAMI"].values])
            )
            ax.contour(
                xx, yy,
                np.reshape(kde_hl(positions).T, xx.shape),
                levels=8,
                cmap="Blues",
                linewidths=1.2
            )
        else:
            print(
                f"  ! Pas assez de points pour "
                f"{highlight_years} ({len(hl)})."
            )

    # ---------------------------------------------------------
    # 2. MARGINALE DU HAUT : distribution du SSMI
    # ---------------------------------------------------------
    x = df["SSMI"].to_numpy()
    x_grid = np.linspace(-QUAD_LIM, QUAD_LIM, 300)

    kde_x = gaussian_kde(x)
    density_x = kde_x(x_grid)

    ax_top.fill_between(
        x_grid, 0, density_x,
        color="#b7e4b0",
        alpha=0.8
    )
    ax_top.plot(
        x_grid, density_x,
        color="#477f42",
        linewidth=1.4
    )

    # Courbe de l'année sélectionnée : ligne seule, sans remplissage
    if highlight_years and len(hl) >= 10:
        x_hl = hl["SSMI"].to_numpy()
        if np.std(x_hl) > 0:
            kde_x_hl = gaussian_kde(x_hl)
            ax_top.plot(
                x_grid, kde_x_hl(x_grid),
                color=plt.cm.Blues(0.85),
                linewidth=1.4
            )

    ax_top.set_xlim(-QUAD_LIM, QUAD_LIM)
    ax_top.set_ylim(bottom=0)
    ax_top.axvline(
        0, color="black", linestyle="--", linewidth=0.8
    )
    ax_top.tick_params(axis="x", bottom=False, labelbottom=False)
    ax_top.tick_params(axis="y", labelsize=8)
    ax_top.set_ylabel("Densité", fontsize=8)

    # ---------------------------------------------------------
    # 3. MARGINALE DE DROITE : distribution du SAMI
    # ---------------------------------------------------------
    y = df["SAMI"].to_numpy()
    y_grid = np.linspace(-QUAD_LIM, QUAD_LIM, 300)

    kde_y = gaussian_kde(y)
    density_y = kde_y(y_grid)

    ax_right.fill_betweenx(
        y_grid, 0, density_y,
        color="#b7e4b0",
        alpha=0.8
    )
    ax_right.plot(
        density_y, y_grid,
        color="#477f42",
        linewidth=1.4
    )

    # Courbe de l'année sélectionnée : ligne seule, sans remplissage
    if highlight_years and len(hl) >= 10:
        y_hl = hl["SAMI"].to_numpy()
        if np.std(y_hl) > 0:
            kde_y_hl = gaussian_kde(y_hl)
            ax_right.plot(
                kde_y_hl(y_grid), y_grid,
                color=plt.cm.Blues(0.85),
                linewidth=1.4
            )

    ax_right.set_ylim(-QUAD_LIM, QUAD_LIM)
    ax_right.set_xlim(left=0)
    ax_right.axhline(
        0, color="black", linestyle="--", linewidth=0.8
    )
    ax_right.tick_params(axis="y", left=False, labelleft=False)
    ax_right.tick_params(axis="x", labelsize=8)
    ax_right.set_xlabel("Densité", fontsize=8)

    # ---------------------------------------------------------
    # 4. TITRE ET SAUVEGARDE
    # ---------------------------------------------------------
    title = "Densité SAMI vs SSMI (saison de croissance)"
    if highlight_years:
        title += f" - contours bleus : {highlight_years}"

    fig.suptitle(title, fontsize=11)
    _save(
        fig, cfg,
        "SAMI_SSMI_quadrants.png",
        dpi=200,
        bbox_inches="tight"
    )


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
    #ax.plot(ssi3.loc[start:end], linewidth=0.9, label="SSI-3 – débit")

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


def plot_indices_year_comparison(sami, ssmi, cfg):
    """
    Compare SAMI et SSMI entre deux années, en alignant les jours
    de chaque année sur une même saison (ex. mai-octobre).
    """

    year1 = cfg.get("comparison_year1", 2024)
    year2 = cfg.get("comparison_year2", 2025)
    start_month = cfg.get("comparison_start_month", 5)
    end_month = cfg.get("comparison_end_month", 10)

    def extract_season(series, year):
        data = series.loc[
            (series.index.year == year)
            & (series.index.month >= start_month)
            & (series.index.month <= end_month)
        ].copy()

        # Aligner les deux années sur une année fictive commune.
        # On utilise 2000 pour permettre le 29 février si nécessaire.
        data.index = pd.to_datetime({
            "year": 2000,
            "month": data.index.month,
            "day": data.index.day
        })

        return data

    sami1 = extract_season(sami, year1)
    sami2 = extract_season(sami, year2)
    ssmi1 = extract_season(ssmi, year1)
    ssmi2 = extract_season(ssmi, year2)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # SAMI
    axes[0].plot(
        sami1.index, sami1.values,
        label=f"SAMI {year1}",
        color="gold",
        linewidth=1.1
    )
    axes[0].plot(
        sami2.index, sami2.values,
        label=f"SAMI {year2}",
        color="darkorange",
        linewidth=1.1
    )
    axes[0].set_ylabel("SAMI (-)")
    axes[0].set_title("Sécheresse atmosphérique")
    axes[0].legend()

    # SSMI
    axes[1].plot(
        ssmi1.index, ssmi1.values,
        label=f"SSMI {year1}",
        color="lightskyblue",
        linewidth=1.1
    )
    axes[1].plot(
        ssmi2.index, ssmi2.values,
        label=f"SSMI {year2}",
        color="blue",
        linewidth=1.1
        )
    axes[1].set_ylabel("SSMI (-)")
    axes[1].set_title("Sécheresse du sol")
    axes[1].legend()
    
    for ax in axes:
        ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
        ax.axhline(-1, color="orange", linestyle="--", linewidth=0.8)
        ax.axhline(-1.5, color="red", linestyle=":", linewidth=0.8)
        ax.axhline(-2, color="darkred", linestyle=":", linewidth=0.8)
        ax.grid(axis="x", linestyle=":", alpha=0.4)

    axes[1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))
    

    fig.suptitle(
        f"Comparaison SAMI et SSMI : {year1} vs {year2}",
        fontsize=14,
        fontweight="bold"
    )

    fig.tight_layout()
    _save(fig, cfg, f"SAMI_SSMI_comparison_{year1}_{year2}.png")

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
        ax.set_xlabel(f"{idx_name}")
        ax.set_ylabel("Densité")
        ax.set_title(f"{idx_name} - scores obtenus et loi normale N(0,1)", fontsize=10)

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

#######################################################""
def plot_quadrant_heatmaps_july(sami, ssmi, cfg):
    """
    Heatmap de la proportion de jours "air sec / sol sec" dans une fenêtre
    glissante de N jours (fenêtre se terminant à la date affichée).
    Axe X : 1er juin -> 30 septembre. Axe Y : années 2000 à 2025.
    """
    start_year, end_year = 2000, 2025
    window = cfg.get("quadrant_window_days", 14)
    sami_thr = cfg.get("quadrant_sami_threshold", cfg.get("event_sami_threshold", -1))
    ssmi_thr = cfg.get("quadrant_ssmi_threshold", cfg.get("event_ssmi_threshold", -1))

    df = pd.concat([sami.rename("SAMI"), ssmi.rename("SSMI")], axis=1).sort_index()
    df = df[~df.index.duplicated(keep="first")]

    # CORRECTION : l'index couvre toute la saison jusqu'au 30 septembre 2025
    # (et commence assez tôt pour que les fenêtres de juin soient complètes).
    full_index = pd.date_range(f"{start_year}-05-01", f"{end_year}-09-30", freq="D")
    df = df.reindex(full_index)

    valid = df["SAMI"].notna() & df["SSMI"].notna()
    dry_both = ((df["SAMI"] < sami_thr) & (df["SSMI"] < ssmi_thr)).astype(float)
    dry_both = dry_both.where(valid)  # NaN si SAMI ou SSMI manquant

    rolling = dry_both.rolling(window=window, min_periods=window).mean() * 100

    # Axe X : 1er juin -> 30 septembre (année fictive non bissextile pour les labels)
    ref_dates = pd.date_range("2025-06-01", "2025-09-30", freq="D")
    years = np.arange(start_year, end_year + 1)

    matrix = np.full((len(years), len(ref_dates)), np.nan)
    for i, year in enumerate(years):
        dates = pd.date_range(f"{year}-06-01", f"{year}-09-30", freq="D")
        matrix[i, :] = rolling.reindex(dates).to_numpy()

    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad("#d9d9d9")

    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(
        np.ma.masked_invalid(matrix),
        origin="upper", aspect="auto", interpolation="nearest",
        extent=(-0.5, len(ref_dates) - 0.5, end_year + 0.5, start_year - 0.5),
        cmap=cmap, vmin=0, vmax=100,
    )

    ax.set_title("Air sec / sol sec")
    ax.set_yticks(years)
    ax.set_ylabel("Année")
    ax.set_xlabel("Date (fin de la fenêtre)")
    ticks = np.arange(0, len(ref_dates), 7)
    ax.set_xticks(ticks)
    ax.set_xticklabels([ref_dates[i].strftime("%d %b") for i in ticks],
                       rotation=45, ha="right")

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("Jours air sec + sol sec (%)")
    cbar.set_ticks([0, 25, 50, 75, 100])

    fig.suptitle(
        f"Sécheresse composée (SAMI < {sami_thr} et SSMI < {ssmi_thr}) - "
        f"fenêtres glissantes de {window} jours ({start_year}-{end_year})",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, cfg, f"quadrant_heatmap_dry_air_dry_soil_{start_year}_{end_year}.png",
          bbox_inches="tight", dpi=200)