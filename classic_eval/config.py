"""Configuration de l'évaluation : TOUT ce qui dépend du site / des fichiers est ici.

Pour un nouveau site ou une nouvelle simulation, on ne modifie que ces valeurs
(via run_evaluation.py) : aucun autre module ne contient de nom de colonne,
de chemin ou de date en dur.
"""
from dataclasses import dataclass, field
from typing import Optional
import warnings
import pandas as pd


@dataclass(frozen=True)
class Period:
    """Période d'analyse. `start` et `end` sont INCLUS (format 'AAAA-MM-JJ')."""
    label: str
    start: str
    end: str

    @property
    def t0(self):
        return pd.Timestamp(self.start)

    @property
    def t1(self):                      # borne exclusive = lendemain de `end`
        return pd.Timestamp(self.end) + pd.Timedelta(days=1)

    @property
    def n_days(self):
        return (self.t1 - self.t0).days


@dataclass(frozen=True)
class Variable:
    """Couple (colonne obs, variable CLASSIC) à évaluer.

    group : "flux" -> figures de l'étape 03 (SW, LE, H, Rn) ; "other" -> étape 05.
    label : nom affiché (par défaut le nom de la colonne obs).
    """
    obs: str
    sim: str
    units: str
    label: Optional[str] = None
    group: str = "other"

    @property
    def name(self):
        return self.label or self.obs


#  valeurs par défaut
# Colonnes des observations (tour à flux). g = flux de chaleur du sol (None si absent).
DEFAULT_OBS_COLS = dict(
    rsd="Rsd_J", rsu="Rsu_J", rld="Rld_J", rlu="Rlu_J",     # rayonnement (SW/LW, bas/haut)
    h="H_J", le="LE_J", g=None,
    ta_forcing="Ta_18m_J_ful", vpd_forcing="VPD_18m_J_ful",  # forçages d'entrée
)

# Variable CLASSIC -> fichier NetCDF. "rootdpth" est traité à part (un profil par PFT).
DEFAULT_CLASSIC_FILES = {
    "hfss": "hfss_halfhourly.nc", "hfls": "hfls_halfhourly.nc", "gflx": "gflx_halfhourly.nc",
    "rsds": "rsds_halfhourly.nc", "rss": "rss_halfhourly.nc",      # SW bas / SW net
    "rlds": "rlds_halfhourly.nc", "rls": "rls_halfhourly.nc",      # LW bas / LW net
    "albs": "albs_halfhourly.nc",
    "snw": "snw_daily.nc", "snc": "snc_daily.nc", "snm": "snm_daily.nc", "snd": "snd_daily.nc",
    "mrsol": "mrsol_daily.nc", "tsl": "tsl_daily.nc", "ts": "ts_halfhourly.nc",
    "pr": "pr_daily.nc", "evspsbl": "evspsbl_daily.nc", "mrro": "mrro_daily.nc",
    "gpp": "gpp_halfhourly.nc", "npp": "npp_daily.nc",
    "evspsblsoi": "evspsblsoi_daily.nc", "evspsblveg": "evspsblveg_daily.nc",
    "rootdpth": "rootdpth_monthly_perpft.nc",
}

# Variables évaluées. Variables DÉRIVÉES calculées automatiquement au chargement :
#   rsus = rsds - rss ; rlus = rlds - rls ; rn = rsds - rsus + rlds - rlus ; "Rn_obs" (obs)
#   nee_proxy = npp x gpp_factor x npp_sign ; et_mmd / et_soi_mmd / et_veg_mmd (mm/j) ; "ET_mm_d" (obs)
DEFAULT_VARIABLES = [
    Variable("Rsu_J", "rsus", "W m-2", "SW réfléchi (SW↑)", "flux"),
    Variable("LE_J", "hfls", "W m-2", "LE", "flux"),
    Variable("H_J", "hfss", "W m-2", "H", "flux"),
    Variable("Rn_obs", "rn", "W m-2", "Rn", "flux"),
    Variable("Rlu_J", "rlus", "W m-2", "LW émis (LW↑)"),
    Variable("Ta_5m_J", "ts", "°C", "Température de surface"),
    Variable("Tsoil_J", "tsl", "°C", "Température du sol"),
    Variable("VWC_CS651_J", "mrsol", "m3 m-3", "Humidité du sol"),
    Variable("GPP_DT_J_gf2", "gpp", "µmol m-2 s-1", "GPP"),
    Variable("NEE_J_gf2", "nee_proxy", "µmol m-2 s-1", "NEE (obs) vs -NPP (CLASSIC)"),
    Variable("ET_mm_d", "et_mmd", "mm j-1", "ET totale"),
]

DEFAULT_SNOW_VARIABLES = {
    "snw": "SWE (kg/m2)", "snc": "Couverture (-)", "snm": "Fonte (kg/m2/s)", "snd": "Profondeur (m)",
}


@dataclass
class EvalConfig:
    # --- chemins 
    obs_dir: str
    classic_dir: str
    output_dir: str
    obs_files: list = field(default_factory=lambda: ["EVAP 1.csv", "EVAP 2.csv"])
    obs_snow_csv: Optional[str] = None       # CSV de hauteur de neige (colonnes time, site, snow_depth en cm)

    # --- description des données 
    time_cols: tuple = ("Year", "Month", "Day", "Hour", "Minute")
    obs_cols: dict = field(default_factory=lambda: dict(DEFAULT_OBS_COLS))
    classic_files: dict = field(default_factory=lambda: dict(DEFAULT_CLASSIC_FILES))
    variables: list = field(default_factory=lambda: list(DEFAULT_VARIABLES))
    snow_variables: dict = field(default_factory=lambda: dict(DEFAULT_SNOW_VARIABLES))
    temperature_obs_cols: tuple = ("Ta_5m_J", "Ta_18m_J_ful", "Tsoil_J")   # converties K -> °C si besoin (auto)

    # --- conversions d'unités CLASSIC 
    gpp_factor: float = 1e9 / 12.011         # kg C m-2 s-1 -> µmol CO2 m-2 s-1
    npp_sign: int = -1                       # NEE = -(production nette) : -1 pour comparer NEE à npp
    et_obs_col: str = "ET_J_ful"             # ET observée (colonne brute)
    et_obs_factor: float = 48.0              # ET_J_ful en mm / 30 min -> mm/j (moyenne x 48). À VÉRIFIER
    g_obs: Optional[str] = "G_J_ful"         # flux de chaleur du sol observé (2e bilan d'énergie)
    soil_layer_thickness: float = 0.1        # m ; mrsol (kg m-2) -> fraction volumique (couche 0 seulement)
    soil_layer: int = 0                      # couche de sol utilisée pour mrsol / tsl
    root_pfts: dict = field(default_factory=lambda: {"PFT 1": 0, "PFT 8": 7})

    # analyses 
    periods: list = field(default_factory=list)   # 5 Period -> 5 graphiques + la moyenne annuelle = 6
    example_year: int = 2021                  # étape 02 : une année complète
    surface_period: Optional[Period] = None   # étape 06 : Ts vs Rn sur cette période
    day: Optional[str] = None                 # étape 08 : jour analysé pour LE ('AAAA-MM-JJ')
    energy_year: int = 2021                   # étape 07 : année du cumul d'énergie
    native_max_days: int = 31                 # période plus longue -> moyennes journalières

    soil_year: int = 2022                     # eau du sol par couche
    root_years: tuple = (2016, 2024)

    snow_sites: tuple = ("LG", "CAN")
    snow_window: tuple = ("2023-10-01", "2025-06-01")   # fenêtre du CSV de neige utilisée
    snow_check_year: int = 2023               # début de l'année hydrologique vérifiée (2023 -> 2023-24)
    snow_threshold_cm: float = 2.0
    melt_frac: float = 0.9
    snow_sim_basis: str = "snd"               # "snd" (hauteur, comme les obs) ou "swe"
    water_years: tuple = (2023,)

    g_sim: Optional[str] = "gflx"             # flux de chaleur du sol CLASSIC (None = ignoré)
    g_sim_sign: int = 1                       # -1 si G est négatif en plein jour d'été
    energy_weighted: bool = True              # pondération mois x heure (voir budgets.py)

    heatmap_vars: list = field(default_factory=lambda: [
        "LE_J", "H_J", "GPP_DT_J_gf2", "Rn_obs", "Rsu_J", "Rlu_J"])
    heatmap_min_n: int = 15                   # nb minimal de points par case (année, mois)

    diurnal_vars: list = field(default_factory=lambda: ["H_J", "LE_J", "Rn_obs", "GPP_DT_J_gf2"])
    responses: list = field(default_factory=lambda: [
        ("GPP_DT_J_gf2", "gpp", "GPP"), ("LE_J", "hfls", "LE"), ("H_J", "hfss", "H")])
    drivers: Optional[dict] = None            # {"TA": (colonne, libellé), ...} ; défaut ci-dessous

    def __post_init__(self):
        if self.drivers is None:
            self.drivers = {
                "TA": (self.obs_cols["ta_forcing"], "Ta (°C)"),
                "VPD": (self.obs_cols["vpd_forcing"], "VPD (kPa)"),
                "SW": (self.obs_cols["rsd"], "SW↓ (W m-2)"),
            }
        if len(self.periods) != 5:
            warnings.warn(f"{len(self.periods)} période(s) définie(s) : le protocole prévoit 5 périodes "
                          "(5 graphiques + moyenne annuelle = 6 par variable).")
