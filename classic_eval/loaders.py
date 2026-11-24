"""Lecture des observations (CSV) et des sorties CLASSIC (NetCDF).

Sortie de load_obs     : DataFrame avec une colonne `Date`.
Sortie de load_classic : dict {nom_variable: DataFrame(Date, nom_variable)}.
Les variables dérivées (rsus, rlus, rn, Rn_obs) sont ajoutées automatiquement.
"""
import gc
import os
import numpy as np
import pandas as pd
import netCDF4 as nc

DERIVED_OBS = {"Rn_obs", "ET_mm_d"}          # colonnes obs calculées, absentes des CSV


# ----------------------------------------------------------------- observations
def _needed_obs_columns(cfg):
    cols = list(cfg.time_cols)
    cols += [v.obs for v in cfg.variables if v.obs not in DERIVED_OBS]
    cols += [c for c in cfg.obs_cols.values() if c]
    cols += [c for c in (cfg.g_obs, cfg.et_obs_col) if c]
    cols += list(cfg.temperature_obs_cols)
    cols += [c for c, _ in cfg.drivers.values()]
    return list(dict.fromkeys(cols))          # sans doublons, ordre conservé


def load_obs(cfg):
    """Concatène les CSV d'observations, construit `Date`, convertit K -> °C, ajoute Rn_obs.

    Seules les colonnes utiles sont lues (économie de mémoire, float32).
    """
    needed = _needed_obs_columns(cfg)

    def read(path):
        header = pd.read_csv(path, nrows=0).columns
        usecols = [c for c in needed if c in header]
        missing = [c for c in needed if c not in header]
        if missing:
            print(f"  colonnes absentes de {os.path.basename(path)} : {missing}")
        dtypes = {c: "float32" for c in usecols if c not in cfg.time_cols}
        return pd.read_csv(path, usecols=usecols, dtype=dtypes)

    print("... lecture des observations")
    obs = pd.concat([read(os.path.join(cfg.obs_dir, f)) for f in cfg.obs_files], ignore_index=True)
    gc.collect()
    parts = obs[list(cfg.time_cols)].set_axis(["year", "month", "day", "hour", "minute"], axis=1)
    obs["Date"] = pd.to_datetime(parts)
    obs = obs.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)

    for col in cfg.temperature_obs_cols:          # K -> °C seulement si la colonne est en Kelvin
        if col in obs.columns and obs[col].median() > 150:
            obs[col] = obs[col] - 273.15
            print(f"  {col} : convertie de K vers °C")

    c = cfg.obs_cols
    if all(c.get(k) in obs.columns for k in ("rsd", "rsu", "rld", "rlu")):
        obs["Rn_obs"] = obs[c["rsd"]] - obs[c["rsu"]] + obs[c["rld"]] - obs[c["rlu"]]
    else:
        print("  Rn_obs non calculable (colonnes de rayonnement manquantes)")
    if cfg.et_obs_col in obs.columns:
        obs["ET_mm_d"] = obs[cfg.et_obs_col] * cfg.et_obs_factor
    print("  observations :", obs.shape)
    return obs


# ----------------------------------------------------------------------- CLASSIC
def read_time(ds):
    """Axe temps d'un NetCDF -> DatetimeIndex (robuste aux calendriers cftime)."""
    t = ds.variables["time"]
    dates = nc.num2date(t[:], units=t.units, calendar=getattr(t, "calendar", "standard"))
    return pd.to_datetime([d.isoformat() for d in dates])


def _to_float(values):
    return np.ma.filled(np.ma.asarray(values, dtype=float), np.nan)


def read_series(path, variable, layer=0):
    """Série (Date, variable) d'un NetCDF à un seul point spatial ; couche `layer` si 4D."""
    ds = nc.Dataset(path)
    try:
        v = ds.variables[variable]
        vals = v[:, layer, 0, 0] if v.ndim == 4 else v[:, 0, 0]
        units = getattr(v, "units", "").strip()
        df = pd.DataFrame({"Date": read_time(ds), variable: _to_float(vals)})
    finally:
        ds.close()
    return df.sort_values("Date").reset_index(drop=True), units


def read_root_depth(path, pfts):
    """Profondeur racinaire (m) par PFT : DataFrame Date + une colonne par PFT demandé."""
    ds = nc.Dataset(path)
    try:
        v = ds.variables["rootdpth"]                       # (time, pft, lat, lon)
        data = {name: _to_float(v[:, idx, 0, 0]) for name, idx in pfts.items()}
        df = pd.DataFrame({"Date": read_time(ds), **data})
    finally:
        ds.close()
    return df.sort_values("Date").reset_index(drop=True)


def load_classic(cfg):
    """Charge toutes les sorties listées dans cfg.classic_files (fichier absent -> ignoré)."""
    print("... lecture de CLASSIC")
    classic = {}
    for name, filename in cfg.classic_files.items():
        path = os.path.join(cfg.classic_dir, filename)
        if not os.path.exists(path):
            print(f"  {name} : fichier absent ({filename}), ignoré")
            continue
        if name == "rootdpth":
            classic[name] = read_root_depth(path, cfg.root_pfts)
            print(f"  {name} ok")
            continue

        df, units = read_series(path, name, cfg.soil_layer)
        if name == "gpp":                                   # kg C m-2 s-1 -> µmol CO2 m-2 s-1
            df[name] *= cfg.gpp_factor
        elif name == "mrsol":                               # kg m-2 -> fraction volumique
            df[name] /= 1000.0 * cfg.soil_layer_thickness
        elif units.lower() in ("k", "kelvin"):              # toute température en Kelvin -> °C
            df[name] -= 273.15
            print(f"  {name} : K -> °C")
        classic[name] = df
        print(f"  {name} ok")

    _add_derived(classic, cfg)
    return classic


def _add_derived(classic, cfg):
    """Variables dérivées : rsus, rlus, rn ; nee_proxy ; ET en mm/j (total, sol, végétation)."""
    if "npp" in classic:        # NEE ~ -NPP (ignore la respiration hétérotrophe : approximation)
        classic["nee_proxy"] = pd.DataFrame({
            "Date": classic["npp"]["Date"],
            "nee_proxy": classic["npp"]["npp"].values * cfg.gpp_factor * cfg.npp_sign})
    for src, out in (("evspsbl", "et_mmd"), ("evspsblsoi", "et_soi_mmd"), ("evspsblveg", "et_veg_mmd")):
        if src in classic:      # kg m-2 s-1 -> mm/j
            classic[out] = pd.DataFrame({"Date": classic[src]["Date"], out: classic[src][src].values * 86400})
    need = {"rsus": ("rsds", "rss"), "rlus": ("rlds", "rls")}
    for out, (down, net) in need.items():
        if down in classic and net in classic:
            classic[out] = pd.DataFrame({
                "Date": classic[down]["Date"],
                out: classic[down][down].values - classic[net][net].values})   # ↑ = ↓ - net
        else:
            print(f"  {out} non calculable ({down}/{net} manquant)")
    if all(k in classic for k in ("rsds", "rsus", "rlds", "rlus")):
        classic["rn"] = pd.DataFrame({
            "Date": classic["rsds"]["Date"],
            "rn": (classic["rsds"]["rsds"].values - classic["rsus"]["rsus"].values
                   + classic["rlds"]["rlds"].values - classic["rlus"]["rlus"].values)})
