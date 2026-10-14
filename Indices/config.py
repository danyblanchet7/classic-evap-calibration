# -*- coding: utf-8 -*-
"""Configuration centrale : tous les parametres modifiables sont ici."""

CONFIG = {
    # --- Donnees d'entree ---
    "point_dir": "C:/Users/danyblanchet7/Desktop/Data analysis/Extraction_FM_J/Juvenil-2020s-EVAP",
    "air_temp_dir": "air_temp",
    "dew_temp_dir": "dew_temp",
    "soil_moisture_dir": "volumetric_soil_water",
    "air_temp_varname": "var167",
    "dew_temp_varname": "var168",
    "soil_moisture_varname": "var40",  # level4 = 100-289 cm
    "streamflow_csv": (
        "C:/Users/danyblanchet7/Desktop/Début Docto/Python/Donnees_debits.csv"
    ),
    "ssi_keep_period": ("2016", "2026"),

    # --- Sortie ---
    "output_dir": "./drought_indices_point_output",

    # --- Standardisation ---
    "ref_period": ("2000-04-01", "2025-09-10"),
    "growing_season_months": (7, 8),

    # --- Graphiques ---
    "display_period": ("2021-07-01", "2021-10-31"),
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
