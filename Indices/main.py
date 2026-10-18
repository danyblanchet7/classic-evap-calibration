
"""
Point d'entree : calcul de SAMI, SSMI et SSI-3 pour un point de grille.

Modules :
  data_loader.py    lecture NetCDF / CSV
  vpd.py            calcul du VPD
  standardization.py  CDF empirique -> score normalisé z
  indices.py        SAMI, SSMI, SSI-3
  events.py         detection d'episodes composes
  propagation.py    correlations croisees decalees
  plots.py          tous les graphiques
"""



CONFIG = {
    # --- Donnees d'entree ---
    "point_dir": "C:/Users/danyblanchet7/Desktop/Data analysis/Extraction_LR/LaRomaine-2020s-EVAP",
    "air_temp_dir": "air_temp",
    "dew_temp_dir": "dew_temp",
    "soil_moisture_dir": "volumetric_soil_water",
    "air_temp_varname": "var167",
    "dew_temp_varname": "var168",
    "soil_moisture_varname": "var40",  # level2 
    "streamflow_csv": (
        "C:/Users/danyblanchet7/Desktop/Début Docto/Python/Donnees_debits.csv"
    ),
    "ssi_keep_period": ("2016", "2024"),

    # --- Sortie ---
    "output_dir": "./drought_indices_point_output",

    # --- Standardisation ---
    "ref_period": ("1970-04-01", "2025-11-10"),
    "growing_season_months": (5, 9),

    # --- Graphiques ---
    "display_period": ("2021-05-01", "2021-10-15"),
    "quadrant_highlight_years": [2024],

    # --- Detection d'episodes de secheresse composee ---
    "event_window_days": 14,
    "event_sami_threshold": -1,
    "event_ssmi_threshold": -1,
    "event_min_duration_days": 14,
    "event_max_gap_days": 7,
    "event_top_n_to_plot": 5,

    # --- Propagation SAMI -> SSMI (journalier) ---
    "propagation_max_lag_days": 30,
    "propagation_min_valid_pairs": 30,

    # --- Propagation SAMI -> SSI-3 (mensuel) ---
    "propagation_sami_ssi_max_lag_months": 6,
    "propagation_sami_ssi_min_valid_pairs": 10,

    "comparison_year1": 2024,
    "comparison_year2": 2025,
    "comparison_start_month": 5,
    "comparison_end_month": 10,


 # --- Analyse des quadrants par fenêtres temporelles ---
    "quadrant_window_days": 14,
    "quadrant_window_step_days": 14,  # fenêtres successives sans chevauchement
    "quadrant_min_valid_days": 14,
    "quadrant_sami_threshold": -1,
    "quadrant_ssmi_threshold": -1,
    "quadrant_sequence_min_fraction": 0.5,
    "quadrant_top_n_windows": 6,
}



import os
import event as events
import indice as indices
import plot as plots
import propagation
import Quadrant 
import pandas as pd


def main(cfg):
    out = cfg["output_dir"]
    os.makedirs(out, exist_ok=True)

    # 1. Indices
    sami, vpd = indices.compute_sami(cfg)
    ssmi, soil = indices.compute_ssmi(cfg)
    ssi3 = indices.compute_ssi3(cfg)
    sami, vpd = indices.compute_sami(cfg)
    ssmi, soil = indices.compute_ssmi(cfg)
    ssi3 = indices.compute_ssi3(cfg)

    # 2. Graphiques descriptifs
    print("\n=== Graphiques descriptifs ===")
    #plots.plot_vpd_reference_period(vpd, cfg)
    #plots.plot_empirical_cdf(vpd, soil, cfg)
    #plots.plot_distributions_and_cdf(vpd, soil, cfg)
    #plots.plot_indices_reference_period(sami, ssmi, cfg)
   # plots.plot_indices_comparison(sami, ssmi, ssi3, cfg)
    plots.plot_quadrant_density(sami, ssmi, cfg)
    plots.plot_indices_year_comparison(sami, ssmi, cfg)
  

    # 3. Episodes de secheresse composee
    print("\n=== Episodes de secheresse composee ===")
  #  events_df = events.detect_compound_dry_events(sami, ssmi, cfg)
 #   if not events_df.empty:
 #       events_df.to_csv(os.path.join(out, "compound_dry_events.csv"), index=False)
 #       print(events_df.to_string(index=False))
 #       plots.plot_quadrant_events(sami, ssmi, events_df, cfg)

    # 4. Propagation SAMI -> SSI-3 (mensuel)
   # print("\n=== Propagation SAMI -> SSI-3 ===")
   # prop_ssi = propagation.analyze_sami_ssi(sami, ssi3, cfg)
   # prop_ssi.to_csv(os.path.join(out, "SAMI_SSI3_lagged_correlation.csv"), index=False)
    #plots.plot_lagged_correlation(
   #     prop_ssi, "lag_months",
   #     "Propagation des anomalies atmosphériques vers la sécheresse hydrologique",
   #     "SAMI_SSI3_lagged_correlation.png", cfg,
   # )

    # 5. Propagation SAMI -> SSMI (journalier)
   # print("\n=== Propagation SAMI -> SSMI ===")
  #  prop_ssmi = propagation.analyze_sami_ssmi(sami, ssmi, cfg)
 #   prop_ssmi.to_csv(os.path.join(out, "SAMI_SSMI_lagged_correlation.csv"), index=False)
  #  plots.plot_lagged_correlation(
  #      prop_ssmi, "lag_days",
  #      "Propagation des anomalies atmosphériques vers l'humidité du sol",
  #      "SAMI_SSMI_lagged_correlation.png", cfg,
  #  )

    # 2. Analyse des quadrants par fenêtres de 14 jours
    print("\n=== Proportions des quadrants par fenêtres ===")

    fractions = Quadrant.compute_quadrant_window_fractions(
        sami, ssmi, cfg
    )

    fractions.to_csv(
        os.path.join(cfg["output_dir"], "quadrant_fractions_14days.csv")
    )

    plots.plot_quadrant_heatmaps_july(sami, ssmi, cfg)

    print(fractions.tail(10).round(3).to_string())
    for name, s in [("SAMI", sami), ("SSMI", ssmi)]:
        v = s.loc["2025"].dropna()
        print(f"{name} 2025 : {v.index.min().date()} -> {v.index.max().date()} "
            f"({len(v)} jours valides)")

    pair = pd.concat([sami, ssmi], axis=1).loc["2025"].dropna()
    season = pd.date_range("2025-07-01", "2025-08-31")
    print("Jours de la saison sans paire valide :", list(season.difference(pair.index).date))
    print("Dernière fenêtre 2025 :", fractions.loc["2025"].index.max().date())
    # Rechercher les séquences air sec / sol sec
    sequences = Quadrant.detect_air_then_soil_sequences(
        fractions, cfg
    )

    sequences.to_csv(
        os.path.join(out, "quadrant_air_then_soil_sequences.csv"),
        index=False
    )

    print("\nSéquences potentielles air sec puis air sec + sol sec :")
    print(sequences.to_string(index=False))

    # Identifier les fenêtres les plus marquées en sécheresse composée
    top_windows = Quadrant.select_top_windows(
        fractions, cfg, column="dry_air_dry_soil"
    )

    print("\nFenêtres les plus marquées en sécheresse composée :")
    for end in top_windows:
        start = end - pd.Timedelta(days=cfg["quadrant_window_days"] - 1)
        print(
            f"{start.date()} au {end.date()} : "
            f"{fractions.loc[end, 'dry_air_dry_soil']:.0%} "
            "des jours avec air sec et sol sec"
        )




main(CONFIG)
