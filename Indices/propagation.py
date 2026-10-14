# -*- coding: utf-8 -*-
"""Analyses de propagation par correlation croisee decalee."""

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def lagged_correlation(x, y, max_lag, min_pairs, freq, lag_col):
    """r(lag) = corr[x(t), y(t + lag)]. Lag > 0 : x precede y.

    freq    : frequence reguliere ("D" ou "ME")
    lag_col : nom de la colonne de decalage ("lag_days" ou "lag_months")
    """
    df = pd.concat([x.rename("x"), y.rename("y")], axis=1).sort_index().asfreq(freq)

    results = []
    for lag in range(-max_lag, max_lag + 1):
        pair = pd.concat([df["x"], df["y"].shift(-lag)], axis=1).dropna()
        n = len(pair)
        if n >= min_pairs:
            r, p = pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
        else:
            r, p = np.nan, np.nan
        results.append({lag_col: lag, "correlation": r, "p_value": p, "n_pairs": n})

    out = pd.DataFrame(results)

    valid = out.dropna(subset=["correlation"])
    if not valid.empty:
        best = out.loc[valid["correlation"].idxmax()]
        unit = lag_col.replace("lag_", "")
        print(f"  Maximum : lag = {best[lag_col]:.0f} {unit}, "
              f"r = {best['correlation']:.3f} ({best['n_pairs']:.0f} paires)")
    return out



def analyze_sami_ssmi(sami, target, cfg):
    """
    Corrélation croisée SAMI -> indice cible (SSMI ou SSI journalier).

    lag_days > 0 : SAMI précède l'indice cible de lag_days jours.
    """
    import numpy as np
    import pandas as pd

    max_lag = cfg["propagation_max_lag_days"]
    min_pairs = cfg["propagation_min_valid_pairs"]

    # Alignement chronologique sur les dates communes
    df = pd.concat(
        [
            sami.rename("SAMI"),
            target.rename("target")
        ],
        axis=1,
        join="inner"
    ).sort_index()

    results = []

    for lag in range(max_lag + 1):

        # Décalage temporel sans décaler les dates elles-mêmes
        if lag == 0:
            x = df["SAMI"].to_numpy(dtype=float)
            y = df["target"].to_numpy(dtype=float)
        else:
            x = df["SAMI"].iloc[:-lag].to_numpy(dtype=float)
            y = df["target"].iloc[lag:].to_numpy(dtype=float)

        # Les deux tableaux ont maintenant la même longueur
        valid = np.isfinite(x) & np.isfinite(y)
        x_valid = x[valid]
        y_valid = y[valid]

        n = len(x_valid)

        if n >= min_pairs and np.std(x_valid) > 0 and np.std(y_valid) > 0:
            r = np.corrcoef(x_valid, y_valid)[0, 1]
        else:
            r = np.nan

        results.append({
            "lag_days": lag,
            "correlation": r,
            "n_pairs": n
        })

    return pd.DataFrame(results)


def analyze_sami_ssi(sami, ssi3, cfg):
    """Propagation mensuelle SAMI (moyenne mensuelle) -> SSI-3."""
    sami_monthly = sami.resample("ME").mean()
    return lagged_correlation(
        sami_monthly, ssi3,
        max_lag=cfg["propagation_sami_ssi_max_lag_months"],
        min_pairs=cfg["propagation_sami_ssi_min_valid_pairs"],
        freq="ME", lag_col="lag_months",
    )
