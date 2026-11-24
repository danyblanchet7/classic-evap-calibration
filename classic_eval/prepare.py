##Mise en correspondance obs / simulation (même pas de temps, mêmes dates).
import numpy as np
import pandas as pd


def merge_exact(obs, sim, obs_variable, sim_variable):
    """Fusion exacte sur les timestamps (inner join). Colonnes : Date, OBS, SIM."""
    o = obs[["Date", obs_variable]].rename(columns={obs_variable: "OBS"})
    s = sim[["Date", sim_variable]].rename(columns={sim_variable: "SIM"})
    return pd.merge(o, s, on="Date", how="inner").dropna()


def daily_mean(df, col, min_frac=0.5):
    """Moyenne journalière ; les jours avec moins de min_frac des données attendues -> NaN."""
    r = df.set_index("Date")[col].resample("1D")
    m, c = r.mean(), r.count()
    m[c < min_frac * c.max()] = np.nan
    return m


def merge_daily(obs, sim, obs_variable, sim_variable, min_frac=0.5):
    """Agrège obs ET sim en moyenne journalière AVANT la fusion.

    Indispensable pour les sorties CLASSIC journalières (mrsol, tsl, snow...) : un inner join
    exact sur Date ne tomberait presque jamais sur les timestamps demi-horaires des obs.
    """
    o = daily_mean(obs, obs_variable, min_frac)
    s = daily_mean(sim, sim_variable, min_frac)
    perf = pd.concat([o, s], axis=1, keys=["OBS", "SIM"]).dropna()
    return perf.rename_axis("Date").reset_index()


def is_daily(sim):
    """True si la sortie CLASSIC a un pas de temps >= 1 jour."""
    d = sim["Date"].diff().dropna()
    return len(d) > 0 and d.median() >= pd.Timedelta(hours=20)


def align(obs, sim, obs_variable, sim_variable, t0=None, t1=None, resolution="native"):
    """Prépare la comparaison obs/sim sur [t0, t1[ (None = tout).

    resolution : "native" -> pas de temps de CLASSIC (demi-horaire, ou journalier si la sortie
                 est journalière) ; "daily" -> moyennes journalières.
    Retourne un DataFrame Date / OBS / SIM (vide si rien en commun).
    """
    if t0 is not None:
        obs = obs[(obs["Date"] >= t0) & (obs["Date"] < t1)]
        sim = sim[(sim["Date"] >= t0) & (sim["Date"] < t1)]
    if resolution == "daily" or is_daily(sim):
        return merge_daily(obs, sim, obs_variable, sim_variable)
    return merge_exact(obs, sim, obs_variable, sim_variable)
