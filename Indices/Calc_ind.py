#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Calculation of SAMI & SSMI pour UN SEUL POINT
de grille (FM).

methode :
  1. VPD journalier a partir de air_temp (t2m) et dew_temp (d2m)
  2. Standardisation par CDF empirique, CONSTRUITE UNIQUEMENT SUR LA
     SAISON DE CROISSANCE (voir CONFIG["growing_season_months"]) et
     sur la periode de reference (cfg["ref_period"]) -> SAMI
  3. Meme standardisation sur l'humidite du sol -> SSMI
  4. Calcul du SSI-3 (debit standardise, via le package `spei`)
  5. Graphique comparatif SAMI / SSMI / SSI-3, avec une periode
     d'affichage ajustable (CONFIG["display_period"])

STRUCTURE ATTENDUE (celle produite par Geoextraction.py) :
    point_dir/
      air_temp/subset_*.nc               (variable var167, en Kelvin)
      dew_temp/subset_*.nc                (variable var168, en Kelvin)
      volumetric_soil_water/subset_*.nc  (variable var39/40/41/42)

"""

import glob
import os
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import scipy.stats as sps
import spei as si
from scipy.stats import norm, gaussian_kde
from scipy.stats import pearsonr


# CONFIG

CONFIG = {
    "point_dir": "C:/Users/danyblanchet7/Desktop/Data analysis/Extraction_FM_J/Juvenil-2020s-EVAP",
    "air_temp_dir": "air_temp",
    "dew_temp_dir": "dew_temp",
    "soil_moisture_dir": "volumetric_soil_water",
        # --- Analyse de propagation SAMI -> SSI-3 ---
    # Lag positif = SAMI précède le SSI-3
    "propagation_sami_ssi_max_lag_months": 6,
    "propagation_sami_ssi_min_valid_pairs": 10,

    # Noms de variables  (convention GRIB brute)
    "air_temp_varname": "var167",
    "dew_temp_varname": "var168",
    "soil_moisture_varname": "var40",  #  level4 = 100-289cm

    "output_dir": "./drought_indices_point_output",

    # Periode de reference utilisee pour construire la CDF empirique
    "ref_period": ("2000-04-01", "2025-09-10"),

    # Mois de la saison de croissance (inclus), utilises pour :
    #   - restreindre la construction de la CDF de reference
    #   - ne calculer les indices standardises QUE sur ces mois
    #     (le reste de l'annee reste NaN)
    # Ajustez selon la phenologie du site (ex: (5, 9) pour mai-sept,
    # (4, 10) pour avril-octobre).
    "growing_season_months": (7, 8),

    # Periode affichee dans le graphique comparatif SAMI/SSMI/SSI-3.
    # Modifiez ces deux dates pour ajuster ce qui est affiche, sans
    # toucher au code de calcul ni de tracage.
    "display_period": ("2021-07-01", "2021-10-31"),

    # Annees a mettre en evidence (contours bleus) par-dessus la
    # densite climatologique complete (verte) dans le graphique a 4
    # cadrants SAMI/SSMI. Mettez None pour ne pas afficher de contour
    # de surbrillance (juste la densite complete). Ex: [2025] pour
    # isoler la secheresse de 2025 evoquee dans vos discussions.
    "quadrant_highlight_years": [2025],

    # --- Detection d'episodes de secheresse "composee" (air + sol) ---
    # Une journee est consideree comme faisant partie d'un episode si
    # la MOYENNE GLISSANTE de SAMI ET de SSMI sur "event_window_days"
    # jours est en dessous des seuils respectifs. Ca capture une
    # secheresse PERSISTANTE (pas juste un jour isole), typiquement du
    # type flash drought (2 semaines a 1 mois).
    "event_window_days": 14,          # taille de la fenetre glissante (jours)
    "event_sami_threshold": -1,     # seuil SAMI (air sec) - "moderee" Peltola
    "event_ssmi_threshold": -1,     # seuil SSMI (sol sec) - "moderee" Peltola
    "event_min_duration_days": 14,    # duree minimale pour retenir un episode
    "event_max_gap_days": 7,          # tolere de courtes interruptions (jours)
    "event_top_n_to_plot": 5,         # nb d'episodes les plus severes a tracer
    # --- Analyse de propagation SAMI -> SSMI ---
    # Lag positif = SAMI précède SSMI
    "propagation_max_lag_days": 30,
    "propagation_min_valid_pairs": 30,
    "threshold_mode": "peltola",
}

PELTOLA_THRESHOLDS = [
    (-np.inf, -2.0, "extreme"),
    (-2.0, -1.5, "grave"),
    (-1.5, -1.0, "moderee"),
    (-1.0, -0.5, "legere"),
    (-0.5, np.inf, "aucune"),
]
PELTOLA_LEGEND = {0: "extreme", 1: "grave", 2: "moderee", 3: "legere", 4: "aucune"}


# --------------------------------------------------------------------
# 1. CHARGEMENT (point unique -> pandas.Series, pas besoin de Dask)
# --------------------------------------------------------------------

def load_point_variable_daily(folder, varname_in_file, agg="mean"):
    """
    Charge tous les fichiers 'subset_*.nc' d'un dossier (un seul pixel
    par fichier), les concatene sur le temps, et retourne une moyenne
    (ou somme) journaliere sous forme de pandas.Series (index = date).
    """
    nc_files = sorted(glob.glob(os.path.join(folder, "**", "*.nc"), recursive=True))
    if not nc_files:
        raise FileNotFoundError(f"Aucun fichier .nc trouve dans {folder}")

    print(f"  -> {len(nc_files)} fichier(s) trouve(s) dans {folder}")

    all_series = []
    for f in nc_files:
        ds = xr.open_dataset(f)
        time_dim = "time" if "time" in ds.dims else "valid_time"
        if time_dim != "time":
            ds = ds.rename({time_dim: "time"})

        if varname_in_file not in ds.data_vars:
            raise KeyError(
                f"Variable '{varname_in_file}' absente de {f}. "
                f"Variables disponibles : {list(ds.data_vars)}"
            )

        da = ds[varname_in_file].squeeze(drop=True)  # enleve les dims lat/lon (taille 1)
        s = da.to_series()
        all_series.append(s)
        ds.close()

    full_series = pd.concat(all_series, sort=False).sort_index()
    full_series = full_series[~full_series.index.duplicated(keep="first")]

    resampler = full_series.resample("1D")
    daily = resampler.mean() if agg == "mean" else resampler.sum()
    daily.name = varname_in_file
    return daily


# --------------------------------------------------------------------
# 2. VPD
# --------------------------------------------------------------------

def compute_vpd(t2m_K, d2m_K):
    """VPD horaire en kPa, puis moyenne journalière."""

    t2m_C = t2m_K - 273.15
    d2m_C = d2m_K - 273.15

    es_air = 0.6108 * np.exp(
        17.27 * t2m_C / (t2m_C + 237.3)
    )

    es_dew = 0.6108 * np.exp(
        17.27 * d2m_C / (d2m_C + 237.3)
    )

    vpd = es_air - es_dew

    # Diagnostic
    print("VPD min avant clipping :", vpd.min())
    print("VPD max avant clipping :", vpd.max())
    print("Nombre de VPD négatifs :", (vpd < 0).sum())

    # On ne clippe pas avant d'avoir vérifié les données
    vpd = vpd.clip(lower=0)

    #vpd = vpd.rolling(7, center=True).mean()

    return vpd.resample("1D").mean().rename("vpd")


# --------------------------------------------------------------------
# 3. STANDARDISATION PAR CDF EMPIRIQUE
#    Methode de Peltola et al. (2026)
# --------------------------------------------------------------------

def _filter_growing_season(index, growing_season_months):
    """
    Retourne un masque booleen (aligne sur `index`) qui vaut True pour
    les dates situees dans la saison de croissance definie par
    growing_season_months = (mois_debut, mois_fin), les deux bornes
    etant incluses (ex: (5, 9) = mai a septembre inclus).
    """
    if growing_season_months is None:
        return np.ones(len(index), dtype=bool)

    start_month, end_month = growing_season_months
    return index.month.isin(range(start_month, end_month + 1))


def empirical_standardize(series, ref_period=None, growing_season_months=None):
    """
    Standardisation par CDF empirique suivant la methode de
    Peltola et al. (2026).

    Principe :
      1. Selection des valeurs de la periode de reference, RESTREINTES
         A LA SAISON DE CROISSANCE (growing_season_months) : la CDF
         n'est plus construite sur l'annee entiere, mais uniquement
         sur les mois de la saison de croissance passee.
      2. Construction d'une CDF empirique a partir de ces valeurs.
      3. Calcul du percentile de chaque observation par rapport
         a cette distribution de reference -- calcule UNIQUEMENT pour
         les jours qui sont eux-memes dans la saison de croissance (le
         reste de l'annee reste NaN, car l'indice n'est pas defini/
         pertinent hors saison de croissance).
      4. Transformation du percentile en score normalise avec
         l'inverse de la CDF normale.

    CORRECTION IMPORTANTE par rapport a la version precedente : la
    probabilite empirique etait calculee comme
        rang / (n_ref + 1)
    ce qui peut valoir EXACTEMENT 0 pour une valeur plus extreme que
    tout ce qui a ete vu dans la periode de reference (de plus en plus
    probable avec des annees recentes/rechauffement climatique) ->
    norm.ppf(0) = -inf, silencieusement. Corrige ici avec une
    plotting-position (rang + 1) / (n_ref + 2), qui reste strictement
    dans (0, 1) meme pour les valeurs record.

    Contrairement a la version d'origine :
      - pas de fenetre glissante selon le jour de l'annee ;
      - pas de combinaison entre les valeurs de reference et
        les valeurs cibles ;
      - une seule distribution empirique est construite a partir
        de la periode de reference ET de la saison de croissance.
    """

    # ---------------------------------------------------------
    # 0. Masque saison de croissance
    # ---------------------------------------------------------

    in_season = _filter_growing_season(series.index, growing_season_months)

    # ---------------------------------------------------------
    # 1. Selection de la periode de reference (ref_period + saison)
    # ---------------------------------------------------------

    if ref_period is not None:

        ref_start = pd.Timestamp(ref_period[0])
        ref_end = pd.Timestamp(ref_period[1])

        ref_mask = (
            (series.index >= ref_start) &
            (series.index <= ref_end) &
            in_season
        )

        reference = series.loc[ref_mask].dropna()

    else:

        reference = series.loc[in_season].dropna()

    # ---------------------------------------------------------
    # 2. Verification
    # ---------------------------------------------------------

    if len(reference) < 10:
        raise ValueError(
            "Pas assez de donnees dans la periode de reference "
            f"(saison de croissance = {growing_season_months}) pour "
            f"construire la CDF empirique ({len(reference)} valeurs)."
        )

    # ---------------------------------------------------------
    # 3. Construction de la distribution empirique
    # ---------------------------------------------------------

    reference_values = np.sort(
        reference.values.astype("float64")
    )

    n_ref = len(reference_values)

    # ---------------------------------------------------------
    # 4. Calcul des probabilites empiriques - UNIQUEMENT pour les
    #    jours de la saison de croissance (le reste reste NaN)
    # ---------------------------------------------------------

    x = series.values.astype("float64")

    valid = np.isfinite(x) & in_season

    probabilities = np.full(
        len(x),
        np.nan,
        dtype="float64"
    )

    # Plotting-position (rang + 1) / (n_ref + 2) : reste dans (0, 1)
    # meme pour une valeur plus extreme que tout l'echantillon de
    # reference (corrige le bug de -inf/+inf de la version precedente)
    probabilities[valid] = (
        np.searchsorted(
            reference_values,
            x[valid],
            side="right"
        ) + 1
    ) / (n_ref + 2)

    # ---------------------------------------------------------
    # 5. Transformation en score normalise
    # ---------------------------------------------------------

    standardized = np.full(
        len(x),
        np.nan,
        dtype="float64"
    )
    standardized[valid] = norm.ppf(
        probabilities[valid]
    )

    return pd.Series(
        standardized,
        index=series.index,
        name=f"{series.name}_standardized"
    )


# --------------------------------------------------------------------
# 5. GRAPHIQUES
# --------------------------------------------------------------------

# Couleurs pour les 5 classes de Peltola (extreme -> aucune)
PELTOLA_COLORS = {0: "#7f0000", 1: "#d7301f", 2: "#fc8d59", 3: "#fdcc8a", 4: "#e0f3f8"}


def detect_compound_dry_events(sami, ssmi, cfg):
    """
    Detecte les episodes de secheresse COMPOSEE (air ET sol secs
    simultanement, de facon persistante) en utilisant une moyenne
    glissante sur SAMI et SSMI.

    Methode :
      1. Moyenne glissante de SAMI et SSMI sur `event_window_days`
         jours (fenetre glissante trainante -- chaque jour resume les
         N derniers jours).
      2. Un jour est "en episode" si LES DEUX moyennes glissantes sont
         sous leurs seuils respectifs (`event_sami_threshold`,
         `event_ssmi_threshold`) -- cadran "Dry air, dry soil" de
         maniere SOUTENUE, pas juste ponctuelle.
      3. Les jours en episode sont regroupes en periodes continues, en
         tolerant de courtes interruptions (`event_max_gap_days`) pour
         ne pas fragmenter un meme evenement a cause d'un jour limite.
      4. Seules les periodes d'au moins `event_min_duration_days` jours
         sont retenues (filtre le bruit court-terme).

    Retourne un DataFrame trie du plus severe au moins severe, avec :
      start, end, duration_days, mean_SAMI, mean_SSMI, min_SAMI,
      min_SSMI, severity (mean_SAMI + mean_SSMI -- plus negatif = pire)
    """
    window = cfg.get("event_window_days", 14)
    sami_thr = cfg.get("event_sami_threshold", -1.0)
    ssmi_thr = cfg.get("event_ssmi_threshold", -1.0)
    min_duration = cfg.get("event_min_duration_days", 14)
    max_gap = cfg.get("event_max_gap_days", 3)

    df = pd.concat([sami.rename("SAMI"), ssmi.rename("SSMI")], axis=1).dropna()
    if len(df) < window:
        print("  ! Pas assez de donnees pour detecter des episodes "
              f"(fenetre de {window} jours demandee, {len(df)} jours disponibles).")
        return pd.DataFrame(columns=[
            "start", "end", "duration_days", "mean_SAMI", "mean_SSMI",
            "min_SAMI", "min_SSMI", "severity",
        ])

    roll_sami = df["SAMI"].rolling(window, min_periods=window).mean()
    roll_ssmi = df["SSMI"].rolling(window, min_periods=window).mean()

    flagged = df.index[(roll_sami < sami_thr) & (roll_ssmi < ssmi_thr)]

    if len(flagged) == 0:
        print("  Aucun episode ne depasse les seuils configures "
              f"(SAMI < {sami_thr} et SSMI < {ssmi_thr} sur {window} jours glissants).")
        return pd.DataFrame(columns=[
            "start", "end", "duration_days", "mean_SAMI", "mean_SSMI",
            "min_SAMI", "min_SSMI", "severity",
        ])

    # --- Regroupement des jours signales en episodes continus,
    #     en tolerant de courtes interruptions (max_gap jours) ---
    episodes_raw = []
    ep_start = flagged[0]
    ep_prev = flagged[0]

    for d in flagged[1:]:
        gap = (d - ep_prev).days
        if gap > max_gap + 1:
            episodes_raw.append((ep_start, ep_prev))
            ep_start = d
        ep_prev = d
    episodes_raw.append((ep_start, ep_prev))

    # --- Statistiques par episode, filtrage duree minimale ---
    rows = []
    for start, end in episodes_raw:
        duration = (end - start).days + 1
        if duration < min_duration:
            continue

        window_data = df.loc[start:end]
        mean_sami = window_data["SAMI"].mean()
        mean_ssmi = window_data["SSMI"].mean()
        rows.append({
            "start": start.date(),
            "end": end.date(),
            "duration_days": duration,
            "mean_SAMI": round(mean_sami, 3),
            "mean_SSMI": round(mean_ssmi, 3),
            "min_SAMI": round(window_data["SAMI"].min(), 3),
            "min_SSMI": round(window_data["SSMI"].min(), 3),
            "severity": round(mean_sami + mean_ssmi, 3),
        })

    events_columns = [
        "start", "end", "duration_days", "mean_SAMI", "mean_SSMI",
        "min_SAMI", "min_SSMI", "severity",
    ]

    if not rows:
        print("  Aucun episode ne dure au moins "
              f"{min_duration} jour(s) apres regroupement "
              f"(seuils : SAMI < {sami_thr}, SSMI < {ssmi_thr}, fenetre {window} j). "
              "Essayez des seuils moins stricts (ex: -0.5) ou une fenetre plus courte "
              "si vous vous attendiez a en trouver.")
        return pd.DataFrame(columns=events_columns)

    events_df = pd.DataFrame(rows, columns=events_columns)
    events_df = events_df.sort_values("severity").reset_index(drop=True)
    return events_df

def analyze_sami_ssmi_propagation(sami, ssmi, cfg):
    """
    Analyse de propagation SAMI -> SSMI par corrélation croisée.

    Convention :
        lag < 0 : SSMI précède SAMI
        lag = 0  : simultané
        lag > 0 : SAMI précède SSMI

    Pour un lag positif :
        r(lag) = corr[SAMI(t), SSMI(t + lag)]
    """

    max_lag = cfg.get("propagation_max_lag_days", 30)
    min_pairs = cfg.get("propagation_min_valid_pairs", 30)

    df = pd.concat(
        [
            sami.rename("SAMI"),
            ssmi.rename("SSMI")
        ],
        axis=1
    ).sort_index()

    # Important : index quotidien régulier
    df = df.asfreq("1D")

    results = []

    for lag in range(-max_lag, max_lag + 1):

        # SSMI(t + lag)
        ssmi_shifted = df["SSMI"].shift(-lag)

        pair = pd.concat(
            [
                df["SAMI"],
                ssmi_shifted.rename("SSMI_shifted")
            ],
            axis=1
        ).dropna()

        n = len(pair)

        if n >= min_pairs:
            r, p = pearsonr(
                pair["SAMI"],
                pair["SSMI_shifted"]
            )
        else:
            r = np.nan
            p = np.nan

        results.append({
            "lag_days": lag,
            "correlation": r,
            "p_value": p,
            "n_pairs": n
        })

    propagation_df = pd.DataFrame(results)

    # Maximum global
    valid = propagation_df.dropna(subset=["correlation"])

    if not valid.empty:
        idx_max = valid["correlation"].idxmax()
        best = propagation_df.loc[idx_max]

        print("\n=== Analyse de propagation SAMI -> SSMI ===")
        print(
            f"Maximum : lag = {best['lag_days']:.0f} jours, "
            f"r = {best['correlation']:.3f}"
        )

        if best["lag_days"] > 0:
            print(
                "Le maximum est à un lag positif : "
                "les anomalies SAMI précèdent statistiquement "
                "les anomalies SSMI."
            )
        elif best["lag_days"] < 0:
            print(
                "Le maximum est à un lag négatif : "
                "les anomalies SSMI précèdent statistiquement "
                "les anomalies SAMI."
            )
        else:
            print(
                "Le maximum est à lag 0 : "
                "pas de décalage temporel apparent."
            )

    return propagation_df

def plot_sami_ssmi_propagation(propagation_df, cfg):
    """
    Trace la corrélation SAMI-SSMI en fonction du décalage temporel.

    Convention :
        lag > 0 = SAMI précède SSMI
        lag < 0 = SSMI précède SAMI
    """

    df = propagation_df.dropna(subset=["correlation"]).copy()

    if df.empty:
        print("  ! Aucun résultat valide à tracer.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(
        df["lag_days"],
        df["correlation"],
        marker="o",
        markersize=3,
        linewidth=1.2
    )

    ax.axhline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    ax.axvline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    # Lag correspondant au maximum de corrélation
    best_idx = df["correlation"].idxmax()
    best_lag = df.loc[best_idx, "lag_days"]
    best_r = df.loc[best_idx, "correlation"]

    ax.scatter(
        best_lag,
        best_r,
        color="red",
        zorder=5,
        label=f"Maximum : lag = {int(best_lag)} j, r = {best_r:.2f}"
    )

    ax.set_xlabel("Décalage temporel (jours)")
    ax.set_ylabel("Corrélation de Pearson (r)")

    ax.set_title(
        "Propagation des anomalies atmosphériques vers l'humidité du sol"
    )

    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    out_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSMI_lagged_correlation.png"
    )

    fig.savefig(
        out_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(
        f"  - Corrélation croisée SAMI/SSMI : "
        f"{os.path.abspath(out_path)}"
    )

def plot_quadrant_events(sami, ssmi, events_df, cfg, top_n=None):
    """
    Reprend le fond de densite du graphique en 4 cadrants et superpose
    la TRAJECTOIRE (SSMI, SAMI) jour par jour des episodes les plus
    severes detectes par detect_compound_dry_events(). Une fleche/point
    marque le debut de chaque trajectoire, pour voir comment le point
    "entre" dans le cadran sec/sec et y reste.
    """
    if top_n is None:
        top_n = cfg.get("event_top_n_to_plot", 5)

    if events_df.empty:
        print("  ! Aucun episode a tracer (events_df est vide).")
        return

    df = pd.concat([ssmi.rename("SSMI"), sami.rename("SAMI")], axis=1).dropna()

    lim = 3.0
    grid = np.linspace(-lim, lim, 200)
    xx, yy = np.meshgrid(grid, grid)
    positions = np.vstack([xx.ravel(), yy.ravel()])

    fig, ax = plt.subplots(figsize=(7.5, 6.5))

    kde_all = gaussian_kde(np.vstack([df["SSMI"].values, df["SAMI"].values]))
    density_all = np.reshape(kde_all(positions).T, xx.shape)
    ax.contourf(xx, yy, density_all, levels=12, cmap="Greens", alpha=0.6)

    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)

    pad = 0.05 * lim
    ax.text(-lim + pad, lim - pad, "Wet air, dry soil", ha="left", va="top", fontsize=9)
    ax.text(lim - pad, lim - pad, "Wet air, wet soil", ha="right", va="top", fontsize=9)
    ax.text(-lim + pad, -lim + pad, "Dry air, dry soil", ha="left", va="bottom", fontsize=9)
    ax.text(lim - pad, -lim + pad, "Dry air, wet soil", ha="right", va="bottom", fontsize=9)

    top_events = events_df.head(top_n)
    colors = plt.cm.plasma(np.linspace(0.1, 0.85, len(top_events)))

    for (_, ev), color in zip(top_events.iterrows(), colors):
        start = pd.Timestamp(ev["start"])
        end = pd.Timestamp(ev["end"])
        traj = df.loc[start:end]
        if traj.empty:
            continue

        label = f"{ev['start']} -> {ev['end']} ({ev['duration_days']} j)"
        ax.plot(traj["SSMI"], traj["SAMI"], color=color, linewidth=1.6,
                marker="o", markersize=2.5, label=label, zorder=5)
        # Marqueur de depart (triangle) et de fin (carre)
        ax.plot(traj["SSMI"].iloc[0], traj["SAMI"].iloc[0], marker="^",
                color=color, markersize=8, zorder=6)
        ax.plot(traj["SSMI"].iloc[-1], traj["SAMI"].iloc[-1], marker="s",
                color=color, markersize=7, zorder=6)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("SSMI (-)")
    ax.set_ylabel("SAMI (-)")
    ax.set_title(
        f"Trajectoires des {len(top_events)} episodes secs les plus severes\n"
        "(triangle = debut, carre = fin)", fontsize=11
    )
    ax.legend(loc="lower right", fontsize=7, framealpha=0.9)

    fig.tight_layout()
    out_path = os.path.join(cfg["output_dir"], "SAMI_SSMI_quadrants_events.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  - Graphique trajectoires d'episodes : {os.path.abspath(out_path)}")


def plot_quadrant_density(sami, ssmi, cfg, highlight_years=None):
    """
    Graphique en 4 cadrants SAMI (y) vs SSMI (x), inspire de la figure
    de l'article discute par l'equipe (Peltola et al. 2026 / meme
    esprit que les figures air sec/sol sec, air sec/sol humide, etc.).

    - Densite pleine (verte) : estimee par KDE sur TOUTES les paires
      (SSMI, SAMI) disponibles (jours de la saison de croissance ou
      les deux indices sont definis).
    - Contours bleus (optionnels) : meme densite, mais restreinte aux
      annees listees dans `highlight_years` (ou cfg["quadrant_highlight_years"]
      si non precise) -- utile pour isoler un evenement particulier
      (ex: la secheresse de 2025) par-dessus la climatologie complete.
    - Lignes pointillees a 0 + labels dans chaque cadrant, comme dans
      la figure de reference.

    Les jours ou SAMI ou SSMI est NaN (hors saison de croissance, ou
    donnees manquantes) sont exclus automatiquement.
    """
    if highlight_years is None:
        highlight_years = cfg.get("quadrant_highlight_years")

    # Alignement des deux series sur les jours communs, valides
    df = pd.concat([ssmi.rename("SSMI"), sami.rename("SAMI")], axis=1).dropna()

    if len(df) < 10:
        print("  ! Pas assez de points valides (SAMI et SSMI simultanement "
              "definis) pour tracer le graphique en 4 cadrants.")
        return

    x_all = df["SSMI"].values
    y_all = df["SAMI"].values

    lim = 3.0  # etendue des axes, comme dans la figure de reference
    grid = np.linspace(-lim, lim, 200)
    xx, yy = np.meshgrid(grid, grid)
    positions = np.vstack([xx.ravel(), yy.ravel()])

    fig, ax = plt.subplots(figsize=(7, 6.5))

    # --- Densite complete (remplie, verte) ---
    kde_all = gaussian_kde(np.vstack([x_all, y_all]))
    density_all = np.reshape(kde_all(positions).T, xx.shape)
    ax.contourf(xx, yy, density_all, levels=12, cmap="Greens")

    # --- Densite d'une sous-periode en surbrillance (contours bleus) ---
    if highlight_years:
        mask_highlight = df.index.year.isin(highlight_years)
        x_hl = df.loc[mask_highlight, "SSMI"].values
        y_hl = df.loc[mask_highlight, "SAMI"].values

        if len(x_hl) >= 10:
            kde_hl = gaussian_kde(np.vstack([x_hl, y_hl]))
            density_hl = np.reshape(kde_hl(positions).T, xx.shape)
            ax.contour(xx, yy, density_hl, levels=8, cmap="Blues", linewidths=1.2)
        else:
            print(f"  ! Pas assez de points pour les annees {highlight_years} "
                  f"({len(x_hl)} trouves) - contour de surbrillance ignore.")

    # --- Lignes/quadrants ---
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)

    pad = 0.05 * lim
    ax.text(-lim + pad, lim - pad, "Wet air, dry soil", ha="left", va="top", fontsize=10)
    ax.text(lim - pad, lim - pad, "Wet air, wet soil", ha="right", va="top", fontsize=10)
    ax.text(-lim + pad, -lim + pad, "Dry air, dry soil", ha="left", va="bottom", fontsize=10)
    ax.text(lim - pad, -lim + pad, "Dry air, wet soil", ha="right", va="bottom", fontsize=10)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("SSMI (-)")
    ax.set_ylabel("SAMI (-)")

    title = "Densite SAMI vs SSMI (saison de croissance)"
    if highlight_years:
        title += f" - contours bleus : {highlight_years}"
    ax.set_title(title, fontsize=11)

    fig.tight_layout()

    out_path = os.path.join(cfg["output_dir"], "SAMI_SSMI_quadrants.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  - Graphique 4 cadrants : {os.path.abspath(out_path)}")


def plot_timeseries(sami, ssmi, cfg):
    """
    Graphique : series temporelles de SAMI et SSMI, avec des zones
    ombragees pour chaque niveau de severite (seuils de Peltola et al.).
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    for ax, series, label, color in zip(
        axes, [sami, ssmi], ["SAMI (air)", "SSMI (sol)"], ["#1f77b4", "#8c564b"]
    ):
        valid = series.dropna()
        ax.plot(valid.index, valid.values, color=color, linewidth=0.8)

        # Zones de severite (ombrage horizontal)
        for lo, hi, _label in PELTOLA_THRESHOLDS:
            lo_plot = max(lo, valid.min() - 0.5) if np.isfinite(lo) else valid.min() - 0.5
            hi_plot = min(hi, valid.max() + 0.5) if np.isfinite(hi) else valid.max() + 0.5
            ax.axhspan(lo_plot, hi_plot, color=PELTOLA_COLORS[
                [i for i, (l, h, lb) in enumerate(PELTOLA_THRESHOLDS) if lb == _label][0]
            ], alpha=0.15, zorder=0)

        ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
        ax.set_ylabel(f"{label}\n(ecart-type)")
        ax.grid(alpha=0.3)

    axes[-1].set_xlabel("Date")
    fig.suptitle("SAMI et SSMI - serie temporelle standardisee", fontsize=13)
    fig.tight_layout()

    out_path = os.path.join(cfg["output_dir"], "SAMI_SSMI_timeseries.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  - Graphique : {os.path.abspath(out_path)}")


def plot_indices_reference_period(sami, ssmi, cfg):
    ref_start = pd.Timestamp(cfg["ref_period"][0])
    ref_end = pd.Timestamp(cfg["ref_period"][1])

    sami_ref = sami.loc[ref_start:ref_end]
    ssmi_ref = ssmi.loc[ref_start:ref_end]

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(
        sami_ref.index,
        sami_ref.values,
        linewidth=0.7,
        label="SAMI"
    )

    ax.plot(
        ssmi_ref.index,
        ssmi_ref.values,
        linewidth=0.7,
        label="SSMI"
    )

    # Seuils Peltola
    ax.axhline(-0.5, linestyle="--", linewidth=0.8)
    ax.axhline(-1.0, linestyle="--", linewidth=0.8)
    ax.axhline(-1.5, linestyle="--", linewidth=0.8)
    ax.axhline(-2.0, linestyle="--", linewidth=0.8)

    ax.axhline(0, linewidth=0.8)

    ax.set_xlabel("Date")
    ax.set_ylabel("Indice standardisé")
    # Titre corrige : reflete les VRAIES dates configurees (plutot que
    # la mention fixe "2011-2020" de la version precedente)
    ax.set_title(
        f"SAMI et SSMI pendant la periode de reference "
        f"({ref_start.date()} - {ref_end.date()})"
    )
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    out_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSMI_reference_period.png"
    )

    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  - Graphique periode de reference : {os.path.abspath(out_path)}")


# --------------------------------------------------------------------
# 6. ORCHESTRATION
# --------------------------------------------------------------------

def compute_ssi(cfg):
    """
    Calcul du SSI-3 a partir des donnees de debit de Montmorency.

    Methode reprise du script de comparaison :
      - lecture des debits journaliers
      - moyenne mensuelle
      - calcul du SSI sur 3 mois avec spei.ssfi()
    """

    print("=== Calcul du SSI-3 (debit standardise) ===")

    debit_path = (
        r"C:/Users/danyblanchet7/Desktop/Début Docto/Python/"
        r"Donnees_debits.csv"
    )

    print("Chargement des donnees de debit ...")

    df_q = pd.read_csv(
        debit_path,
        sep=";",
        decimal=".",
        encoding="latin1"
    )

    # Date
    df_q["Date"] = pd.to_datetime(
        df_q["Date"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    # Debit numerique
    df_q["Débit(m³/s)"] = pd.to_numeric(
        df_q["Débit(m³/s)"],
        errors="coerce"
    )

    df_q = df_q.dropna(
        subset=["Date", "Débit(m³/s)"]
    )

    df_q = df_q.set_index("Date")

    # Moyenne mensuelle
    monthly_q = df_q["Débit(m³/s)"].resample("ME").mean()

    print("\n===== DEBIT MENSUEL =====")
    print(monthly_q.describe())

    # SSI-3
    print("\nCalcul du SSI-3 ...")

    ssi3_all = si.ssfi(
        monthly_q,
        dist=sps.gamma,
        timescale=3
    )

    # On conserve la periode correspondant a nos donnees
    ssi3 = ssi3_all.loc["2016":"2026"].copy()

    # Si spei retourne une Series avec un nom particulier
    ssi3.name = "SSI-3"

    print("\n===== SSI-3 =====")
    print(ssi3.describe())

    return ssi3

def analyze_sami_ssi_propagation(sami, ssi3, cfg):
    """
    Analyse de la propagation SAMI -> SSI-3 par correlation croisee.

    Le SAMI est journalier, tandis que le SSI-3 est mensuel.
    Le SAMI est donc d'abord agrege en moyenne mensuelle.

    Convention :
        lag < 0 : SSI-3 precede SAMI
        lag = 0 : SAMI et SSI-3 du meme mois
        lag > 0 : SAMI precede SSI-3

    Pour un lag positif :
        r(lag) = corr[SAMI(t), SSI3(t + lag)]
    """

    max_lag = cfg.get(
        "propagation_sami_ssi_max_lag_months",
        6
    )

    min_pairs = cfg.get(
        "propagation_sami_ssi_min_valid_pairs",
        10
    )

    # ---------------------------------------------------------
    # SAMI journalier -> moyenne mensuelle
    # ---------------------------------------------------------

    sami_monthly = sami.resample("ME").mean()
    sami_monthly.name = "SAMI"

    # ---------------------------------------------------------
    # Alignement avec le SSI-3 mensuel
    # ---------------------------------------------------------

    df = pd.concat(
        [
            sami_monthly,
            ssi3.rename("SSI3")
        ],
        axis=1
    ).sort_index()

    # Index mensuel regulier
    df = df.asfreq("ME")

    results = []

    # ---------------------------------------------------------
    # Correlation croisee
    # ---------------------------------------------------------

    for lag in range(-max_lag, max_lag + 1):

        # SSI3(t + lag)
        ssi_shifted = df["SSI3"].shift(-lag)

        pair = pd.concat(
            [
                df["SAMI"],
                ssi_shifted.rename("SSI3_shifted")
            ],
            axis=1
        ).dropna()

        n = len(pair)

        if n >= min_pairs:
            r, p = sps.pearsonr(
                pair["SAMI"],
                pair["SSI3_shifted"]
            )
        else:
            r = np.nan
            p = np.nan

        results.append(
            {
                "lag_months": lag,
                "correlation": r,
                "p_value": p,
                "n_pairs": n
            }
        )

    propagation_df = pd.DataFrame(results)

    # ---------------------------------------------------------
    # Maximum de correlation
    # ---------------------------------------------------------

    valid = propagation_df.dropna(
        subset=["correlation"]
    )

    if not valid.empty:

        idx_max = valid["correlation"].idxmax()

        best = propagation_df.loc[idx_max]

        print(
            "\n=== Propagation SAMI -> SSI-3 ==="
        )

        print(
            f"Maximum : lag = "
            f"{best['lag_months']:.0f} mois, "
            f"r = {best['correlation']:.3f}"
        )

        print(
            f"Nombre de paires : "
            f"{best['n_pairs']:.0f}"
        )

        if best["lag_months"] > 0:

            print(
                "Le maximum est a un lag positif : "
                "les anomalies SAMI precedent "
                "statistiquement les anomalies SSI-3."
            )

        elif best["lag_months"] < 0:

            print(
                "Le maximum est a un lag negatif : "
                "les anomalies SSI-3 precedent "
                "statistiquement les anomalies SAMI."
            )

        else:

            print(
                "Le maximum est a lag 0 : "
                "pas de decalage mensuel apparent."
            )

    return propagation_df

def plot_sami_ssi_propagation(propagation_df, cfg):
    """
    Trace la correlation croisee entre le SAMI mensuel
    et le SSI-3 pour differents decalages temporels.
    """

    valid = propagation_df.dropna(
        subset=["correlation"]
    )

    if valid.empty:
        print(
            "Aucune correlation disponible pour "
            "le graphique SAMI -> SSI-3."
        )
        return

    # Maximum
    idx_max = valid["correlation"].idxmax()
    best = propagation_df.loc[idx_max]

    fig, ax = plt.subplots(
        figsize=(14, 6)
    )

    ax.plot(
        propagation_df["lag_months"],
        propagation_df["correlation"],
        marker="o",
        linewidth=1.2
    )

    # Ligne verticale a lag 0
    ax.axvline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    # Ligne horizontale a r = 0
    ax.axhline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    # Maximum
    ax.scatter(
        best["lag_months"],
        best["correlation"],
        color="red",
        s=80,
        zorder=5,
        label=(
            f"Maximum : lag = "
            f"{best['lag_months']:.0f} mois, "
            f"r = {best['correlation']:.2f}"
        )
    )

    ax.set_xlabel(
        "Décalage temporel (mois)"
    )

    ax.set_ylabel(
        "Corrélation de Pearson (r)"
    )

    ax.set_title(
        "Propagation des anomalies atmosphériques "
        "vers la sécheresse hydrologique"
    )

    ax.legend(
        loc="best"
    )

    ax.grid(
        alpha=0.3
    )

    fig.tight_layout()

    out_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSI3_lagged_correlation.png"
    )

    fig.savefig(
        out_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(
        "  - Graphique propagation SAMI -> SSI-3 : "
        f"{os.path.abspath(out_path)}"
    )
def compute_sami(cfg):
    print("=== Calcul du SAMI (VPD standardise) ===")
    print("Chargement de air_temp ...")
    t2m = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["air_temp_dir"]),
        cfg["air_temp_varname"], agg="mean",
    )
    print("Chargement de dew_temp ...")
    d2m = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["dew_temp_dir"]),
        cfg["dew_temp_varname"], agg="mean",
    )

    print("Calcul du VPD journalier ...")
    vpd = compute_vpd(t2m, d2m)
    plot_reference_period(vpd, cfg)

    print("\n===== T2M =====")
    print(t2m.describe())
    print(t2m.head(10))

    print("\n===== D2M =====")
    print(d2m.describe())
    print(d2m.head(10))

    print("\n===== T2M - D2M =====")
    tdiff = t2m - d2m
    print(tdiff.describe())
    print("Nombre Td > T :", (tdiff < 0).sum())
    print("Nombre total :", len(tdiff))

    print("\n===== VPD =====")
    print(vpd.describe())
    print(vpd.head(10))

    print("Standardisation (CDF empirique, saison de croissance uniquement) ...")
    sami = empirical_standardize(
        vpd,
        ref_period=cfg["ref_period"],
        growing_season_months=cfg.get("growing_season_months"),
    )

    # Peltola et al. :
    # SAMI = - Phi^-1(F_VPD(VPD))
    #
    # Une forte VPD correspond donc a un SAMI negatif.
    sami = -sami

    sami.name = "SAMI"
    return sami


def compute_ssmi(cfg):
    print("=== Calcul du SSMI (humidite du sol standardisee) ===")
    print("Chargement de volumetric_soil_water ...")
    soil = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["soil_moisture_dir"]),
        cfg["soil_moisture_varname"], agg="mean",
    )

    print("Standardisation (CDF empirique, saison de croissance uniquement) ...")
    ssmi = empirical_standardize(
        soil,
        ref_period=cfg["ref_period"],
        growing_season_months=cfg.get("growing_season_months"),
    )

    # Peltola et al. :
    # SSMI = Phi^-1(F_VWC(VWC))
    #
    # Une faible humidite du sol correspond donc a un SSMI negatif.
    ssmi.name = "SSMI"
    return ssmi


def plot_reference_period(vpd, cfg):
    ref_start = pd.Timestamp(cfg["ref_period"][0])
    ref_end = pd.Timestamp(cfg["ref_period"][1])

    fig, ax = plt.subplots(figsize=(14, 5))

    # Toute la série
    ax.plot(
        vpd.index,
        vpd.values,
        linewidth=0.7,
        label="VPD"
    )

    # Période de référence
    ref = vpd.loc[ref_start:ref_end]

    ax.plot(
        ref.index,
        ref.values,
        linewidth=0.8,
        label="VPD - période de référence"
    )

    ax.axvspan(
        ref_start,
        ref_end,
        alpha=0.15,
        label="Période de référence"
    )

    ax.set_ylabel("VPD (kPa)")
    ax.set_xlabel("Date")
    ax.set_title("VPD et période de référence")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    out_path = os.path.join(
        cfg["output_dir"],
        "VPD_reference_period.png"
    )

    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"  - Graphique période de référence : {os.path.abspath(out_path)}")


def plot_reference_by_doy(vpd, cfg):
    ref_start = pd.Timestamp(cfg["ref_period"][0])
    ref_end = pd.Timestamp(cfg["ref_period"][1])

    ref = vpd.loc[ref_start:ref_end].copy()

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.scatter(
        ref.index.dayofyear,
        ref.values,
        s=4,
        alpha=0.4
    )

    ax.set_xlabel("Jour de l'année")
    ax.set_ylabel("VPD (kPa)")
    ax.set_title("Distribution du VPD pendant la période de référence")
    ax.grid(alpha=0.3)

    fig.tight_layout()

    out_path = os.path.join(
        cfg["output_dir"],
        "VPD_reference_by_DOY.png"
    )

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_indices_comparison(sami, ssmi, ssi3, cfg):
    """
    Compare SAMI, SSMI et SSI-3 sur une meme figure.

    SAMI : secheresse atmospherique
    SSMI : secheresse du sol
    SSI-3 : secheresse hydrologique (debit, accumulation 3 mois)

    La periode AFFICHEE (pas la periode de CALCUL) est controlee par
    cfg["display_period"] = (date_debut, date_fin) -- modifiez cette
    entree dans CONFIG pour ajuster ce qui est trace, sans avoir a
    toucher au reste du script.
    """

    # ---------------------------------------------------------
    # Periode affichee (ajustable via cfg["display_period"])
    # ---------------------------------------------------------

    start = pd.Timestamp(cfg["display_period"][0])
    end = pd.Timestamp(cfg["display_period"][1])

    sami_plot = sami.loc[start:end]
    ssmi_plot = ssmi.loc[start:end]
    ssi_plot = ssi3.loc[start:end]

    # ---------------------------------------------------------
    # Figure
    # ---------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(16, 6)
    )

    fig.suptitle(
        f"Comparaison des indices de sécheresse – Montmorency "
        f"({start.date()} – {end.date()})",
        fontsize=14,
        fontweight="bold"
    )

    # ---------------------------------------------------------
    # SAMI
    # ---------------------------------------------------------

    ax.plot(
        sami_plot.index,
        sami_plot.values,
        linewidth=0.8,
        label="SAMI – atmosphère"
    )

    # ---------------------------------------------------------
    # SSMI
    # ---------------------------------------------------------

    ax.plot(
        ssmi_plot.index,
        ssmi_plot.values,
        linewidth=0.8,
        label="SSMI – sol"
    )

    # ---------------------------------------------------------
    # SSI-3
    # ---------------------------------------------------------

    ax.plot(
        ssi_plot.index,
        ssi_plot.values,
        linewidth=0.9,
        label="SSI-3 – débit"
    )

    # ---------------------------------------------------------
    # Ligne 0
    # ---------------------------------------------------------

    ax.axhline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    # ---------------------------------------------------------
    # Seuils de sécheresse
    # ---------------------------------------------------------

    ax.axhline(
        -1,
        color="orange",
        linestyle="--",
        linewidth=0.8,
        label="Modérée (−1)"
    )

    ax.axhline(
        -1.5,
        color="red",
        linestyle="--",
        linewidth=0.8,
        label="Sévère (−1.5)"
    )

    ax.axhline(
        -2,
        color="darkred",
        linestyle="--",
        linewidth=0.8,
        label="Extrême (−2)"
    )

    # ---------------------------------------------------------
    # Axe Y
    # ---------------------------------------------------------

    ax.set_ylabel(
        "Indice standardisé"
    )

    ax.set_ylim(
        -3.5,
        3.5
    )

    # ---------------------------------------------------------
    # Axe X
    # ---------------------------------------------------------

    ax.set_xlabel("Date")

    ax.xaxis.set_major_locator(
        mdates.YearLocator()
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%Y")
    )

    ax.xaxis.set_minor_locator(
        mdates.MonthLocator(
            bymonth=[4, 7, 10]
        )
    )

    plt.setp(
        ax.xaxis.get_majorticklabels(),
        rotation=45,
        ha="right"
    )

    # ---------------------------------------------------------
    # Grille / legende
    # ---------------------------------------------------------

    ax.grid(
        axis="x",
        linestyle=":",
        alpha=0.5
    )

    ax.legend(
        loc="upper right",
        fontsize=9
    )

    fig.tight_layout()

    # ---------------------------------------------------------
    # Sauvegarde
    # ---------------------------------------------------------

    out_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSMI_SSI3_comparison.png"
    )

    fig.savefig(
        out_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(
        f"  - Graphique comparaison : "
        f"{os.path.abspath(out_path)}"
    )


def main(cfg):

    os.makedirs(
        cfg["output_dir"],
        exist_ok=True
    )

    sami = compute_sami(cfg)

    ssmi = compute_ssmi(cfg)

    ssi3 = compute_ssi(cfg)

    # Comparaison SAMI / SSMI / SSI-3 (periode affichee ajustable via
    # cfg["display_period"])
    plot_indices_comparison(
        sami,
        ssmi,
        ssi3,
        cfg
    )
    # ---------------------------------------------------------
    # Propagation SAMI -> SSI-3
    # ---------------------------------------------------------

    propagation_sami_ssi = analyze_sami_ssi_propagation(
        sami,
        ssi3,
        cfg
    )

    propagation_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSI3_lagged_correlation.csv"
    )

    propagation_sami_ssi.to_csv(
        propagation_path,
        index=False
    )

    print(
        "  - Correlation croisee SAMI -> SSI-3 : "
        f"{os.path.abspath(propagation_path)}"
    )

    plot_sami_ssi_propagation(
        propagation_sami_ssi,
        cfg
    )
    # Graphique de la periode de reference
    plot_indices_reference_period(
        sami,
        ssmi,
        cfg
    )

    # Graphique en 4 cadrants (densite SAMI vs SSMI)
    plot_quadrant_density(sami, ssmi, cfg)

    # Detection des episodes de secheresse composee (air + sol,
    # persistants, 2 semaines a 1 mois) + trajectoires sur la carte 2D
    print("=== Detection des episodes de secheresse composee ===")
    events_df = detect_compound_dry_events(sami, ssmi, cfg)
    if not events_df.empty:
        events_path = os.path.join(cfg["output_dir"], "compound_dry_events.csv")
        events_df.to_csv(events_path, index=False)
        print(f"  - {len(events_df)} episode(s) detecte(s), sauvegardes dans : "
              f"{os.path.abspath(events_path)}")
        print(events_df.to_string(index=False))
        plot_quadrant_events(sami, ssmi, events_df, cfg)
    # ---------------------------------------------------------
    # Analyse de propagation SAMI -> SSMI
    # ---------------------------------------------------------

    print("\n=== Analyse de propagation SAMI -> SSMI ===")

    propagation_df = analyze_sami_ssmi_propagation(
        sami,
        ssmi,
        cfg
    )

    propagation_path = os.path.join(
        cfg["output_dir"],
        "SAMI_SSMI_lagged_correlation.csv"
    )

    propagation_df.to_csv(
        propagation_path,
        index=False
    )

    print(
        f"  - Résultats sauvegardés dans : "
        f"{os.path.abspath(propagation_path)}"
    )

    plot_sami_ssmi_propagation(
        propagation_df,
        cfg
    )

if __name__ == "__main__":
    main(CONFIG)