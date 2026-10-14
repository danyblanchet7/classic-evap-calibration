
"""
Point d'entree : calcul de SAMI, SSMI et SSI-3 pour un point de grille.

Modules :
  data_loader.py    lecture NetCDF / CSV
  vpd.py            calcul du VPD
  standardization.py  CDF empirique -> score z
  indices.py        SAMI, SSMI, SSI-3
  events.py         detection d'episodes composes
  propagation.py    correlations croisees decalees
  plots.py          tous les graphiques
"""



CONFIG = {
    # --- Donnees d'entree ---
    "point_dir": "C:/Users/danyblanchet7/Desktop/Data analysis/Extraction_FM_J/Juvenil-2020s-EVAP",
    "air_temp_dir": "air_temp",
    "dew_temp_dir": "dew_temp",
    "soil_moisture_dir": "volumetric_soil_water",
    "air_temp_varname": "var167",
    "dew_temp_varname": "var168",
    "soil_moisture_varname": "var40",  # level2 
    "streamflow_csv": (
        "C:/Users/danyblanchet7/Desktop/Début Docto/Python/Donnees_debits.csv"
    ),
    "ssi_keep_period": ("2016", "2026"),

    # --- Sortie ---
    "output_dir": "./drought_indices_point_output",

    # --- Standardisation ---
    "ref_period": ("1980-04-01", "2020-11-10"),
    "growing_season_months": (5, 9),

    # --- Graphiques ---
    "display_period": ("2025-05-01", "2025-08-15"),
    "quadrant_highlight_years": [2025],

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
}



import os
import event as events
import indice as indices
import plot as plots
import propagation



def main(cfg):
    out = cfg["output_dir"]
    os.makedirs(out, exist_ok=True)

    # 1. Indices
    sami, vpd = indices.compute_sami(cfg)
    ssmi, soil = indices.compute_ssmi(cfg)
    ssi3 = indices.compute_ssi3(cfg)

    # 2. Graphiques descriptifs
    print("\n=== Graphiques descriptifs ===")
    plots.plot_vpd_reference_period(vpd, cfg)
    plots.plot_empirical_cdf(vpd, soil, cfg)
    plots.plot_distributions_and_cdf(vpd, soil, cfg)
    plots.plot_indices_reference_period(sami, ssmi, cfg)
    plots.plot_indices_comparison(sami, ssmi, ssi3, cfg)
    plots.plot_quadrant_density(sami, ssmi, cfg)

    # 3. Episodes de secheresse composee
    print("\n=== Episodes de secheresse composee ===")
    events_df = events.detect_compound_dry_events(sami, ssmi, cfg)
    if not events_df.empty:
        events_df.to_csv(os.path.join(out, "compound_dry_events.csv"), index=False)
        print(events_df.to_string(index=False))
        plots.plot_quadrant_events(sami, ssmi, events_df, cfg)

    # 4. Propagation SAMI -> SSI-3 (mensuel)
    print("\n=== Propagation SAMI -> SSI-3 ===")
    prop_ssi = propagation.analyze_sami_ssi(sami, ssi3, cfg)
    prop_ssi.to_csv(os.path.join(out, "SAMI_SSI3_lagged_correlation.csv"), index=False)
    plots.plot_lagged_correlation(
        prop_ssi, "lag_months",
        "Propagation des anomalies atmosphériques vers la sécheresse hydrologique",
        "SAMI_SSI3_lagged_correlation.png", cfg,
    )

    # 5. Propagation SAMI -> SSMI (journalier)
    print("\n=== Propagation SAMI -> SSMI ===")
    prop_ssmi = propagation.analyze_sami_ssmi(sami, ssmi, cfg)
    prop_ssmi.to_csv(os.path.join(out, "SAMI_SSMI_lagged_correlation.csv"), index=False)
    plots.plot_lagged_correlation(
        prop_ssmi, "lag_days",
        "Propagation des anomalies atmosphériques vers l'humidité du sol",
        "SAMI_SSMI_lagged_correlation.png", cfg,
    )




main(CONFIG)
