# -*- coding: utf-8 -*-
"""Calcul des trois indices : SAMI (air), SSMI (sol), SSI-3 (debit)."""

import os

import scipy.stats as sps
import spei as si

from data_loader import load_monthly_streamflow, load_point_variable_daily
from standardization import empirical_standardize
from vpd import compute_vpd


def compute_sami(cfg):
    """Retourne (SAMI, VPD). SAMI = -Phi^-1(F_VPD(VPD)) : VPD eleve -> SAMI negatif."""
    print("=== Calcul du SAMI (VPD standardise) ===")
    t2m = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["air_temp_dir"]), cfg["air_temp_varname"]
    )
    d2m = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["dew_temp_dir"]), cfg["dew_temp_varname"]
    )

    vpd = compute_vpd(t2m, d2m)
    sami = -empirical_standardize(
        vpd, cfg["ref_period"], cfg["growing_season_months"]
    )
    sami.name = "SAMI"
    return sami, vpd


def compute_ssmi(cfg):
    """Retourne (SSMI, humidite brute). SSMI = Phi^-1(F_VWC(VWC)) : sol sec -> SSMI negatif."""
    print("=== Calcul du SSMI (humidite du sol standardisee) ===")
    soil = load_point_variable_daily(
        os.path.join(cfg["point_dir"], cfg["soil_moisture_dir"]),
        cfg["soil_moisture_varname"],
    )
    ssmi = empirical_standardize(
        soil, cfg["ref_period"], cfg["growing_season_months"]
    )
    ssmi.name = "SSMI"
    return ssmi, soil


def compute_ssi3(cfg):
    """SSI-3 : debit mensuel standardise (gamma) sur 3 mois, via `spei`."""
    print("=== Calcul du SSI-3 (debit standardise) ===")
    monthly_q = load_monthly_streamflow(cfg["streamflow_csv"])

    ssi3_all = si.ssfi(monthly_q, dist=sps.gamma, timescale=3)
    start, end = cfg["ssi_keep_period"]
    ssi3 = ssi3_all.loc[start:end].copy()
    ssi3.name = "SSI-3"
    return ssi3
