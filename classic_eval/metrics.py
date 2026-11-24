"""Métriques quantitatives : Biais, RMSE, MAE, r, R², NSE, KGE, déphasage, IAV.

Convention : Biais = moyenne(SIM - OBS)  (> 0 => le modèle surestime).
R² = r² (carré de la corrélation). NSE = 1 - SSE/SST (peut être négatif).
"""
import numpy as np


def _clean(obs, sim):
    obs, sim = np.asarray(obs, float), np.asarray(sim, float)
    m = np.isfinite(obs) & np.isfinite(sim)
    return obs[m], sim[m]


def rmse(obs, sim):
    return float(np.sqrt(np.mean((sim - obs) ** 2)))


def mae(obs, sim):
    return float(np.mean(np.abs(sim - obs)))


def bias(obs, sim):
    return float(np.mean(sim - obs))


def correlation(obs, sim):
    if np.std(obs) == 0 or np.std(sim) == 0:
        return np.nan
    return float(np.corrcoef(obs, sim)[0, 1])


def nse(obs, sim):
    den = np.sum((obs - obs.mean()) ** 2)
    return float(1 - np.sum((obs - sim) ** 2) / den) if den > 0 else np.nan


def kge(obs, sim):
    """Kling-Gupta efficiency (2009)."""
    r = correlation(obs, sim)
    if obs.mean() == 0 or obs.std() == 0 or np.isnan(r):
        return np.nan
    return float(1 - np.sqrt((r - 1) ** 2 + (sim.std() / obs.std() - 1) ** 2
                             + (sim.mean() / obs.mean() - 1) ** 2))


def nrmse(obs, sim):
    """RMSE normalisé par l'écart-type des obs."""
    s = obs.std()
    return float(rmse(obs, sim) / s) if s > 0 else np.nan


def calculate_metrics(obs, sim):
    """Dictionnaire de métriques ; {"N": n} seul si moins de 2 points communs."""
    obs, sim = _clean(obs, sim)
    if len(obs) < 2:
        return {"N": len(obs)}
    r = correlation(obs, sim)
    return {"N": len(obs), "RMSE": rmse(obs, sim), "NRMSE": nrmse(obs, sim),
            "MAE": mae(obs, sim), "Bias": bias(obs, sim), "r": r, "R2": r ** 2,
            "NSE": nse(obs, sim), "KGE": kge(obs, sim)}


def phase_shift(obs, sim, step_hours=0.5, max_lag_hours=6.0, circular=False):
    """Décalage temporel (heures) qui maximise la corrélation obs/sim.

    > 0 : le modèle est EN RETARD sur les observations.
    circular=True pour un cycle diurne moyen (série périodique).
    """
    obs, sim = np.asarray(obs, float), np.asarray(sim, float)
    max_lag = int(round(max_lag_hours / step_hours))
    best_lag, best_r = 0, -np.inf
    for lag in range(-max_lag, max_lag + 1):
        if circular:
            o, s = obs, np.roll(sim, -lag)
        elif lag >= 0:
            o, s = obs[:len(obs) - lag], sim[lag:]
        else:
            o, s = obs[-lag:], sim[:len(sim) + lag]
        m = np.isfinite(o) & np.isfinite(s)
        if m.sum() < 3 or np.std(o[m]) == 0 or np.std(s[m]) == 0:
            continue
        r = np.corrcoef(o[m], s[m])[0, 1]
        if r > best_r:
            best_r, best_lag = r, lag
    return best_lag * step_hours


def iav(perf, min_frac=0.8):
    """Variabilité interannuelle (perf : Date/OBS/SIM, idéalement journalier).

    Compare les moyennes annuelles (années assez complètes seulement) : écart-type
    interannuel obs vs sim et corrélation des anomalies.
    """
    d = perf.dropna(subset=["OBS", "SIM"])
    g = d.groupby(d["Date"].dt.year)
    ann, cnt = g[["OBS", "SIM"]].mean(), g.size()
    ann = ann[cnt >= min_frac * cnt.max()]
    if len(ann) < 3:
        return {"IAV_obs": np.nan, "IAV_sim": np.nan, "IAV_r": np.nan, "IAV_nyears": len(ann)}
    anom = ann - ann.mean()
    return {"IAV_obs": float(ann["OBS"].std()), "IAV_sim": float(ann["SIM"].std()),
            "IAV_r": correlation(anom["OBS"].values, anom["SIM"].values),
            "IAV_nyears": int(len(ann))}
