
# Standardisation par CDF empirique (Peltola et al. 2026)

import numpy as np
import pandas as pd
from scipy.stats import norm


def growing_season_mask(index, growing_season_months):
 #Masque booleen : True pour les dates dans la saison de croissance (mois de debut et de fin inclus).

    start_month, end_month = growing_season_months
    return index.month.isin(range(start_month, end_month + 1))


def reference_values(series, ref_period, growing_season_months):
#Valeurs TRIEES formant la distribution de reference : jours situes dans ref_period ET dans la saison de croissance. C'est la CDF empirique.
    in_season = growing_season_mask(series.index, growing_season_months)

    if ref_period is not None:
        ref_start, ref_end = pd.Timestamp(ref_period[0]), pd.Timestamp(ref_period[1])
        ref_mask = (series.index >= ref_start) & (series.index <= ref_end) & in_season
        reference = series.loc[ref_mask].dropna()
    else:
        reference = series.loc[in_season].dropna()

    if len(reference) < 10:
        raise ValueError(
            f"Pas assez de donnees de reference ({len(reference)} valeurs, "
            f"saison = {growing_season_months})."
        )
    return np.sort(reference.values.astype("float64"))


#2. Calcule pour chaque valeur sa position (rang percentile) dans la distribution. 

def empirical_probability(ref_sorted, x):
    k = np.searchsorted(ref_sorted, x, side="right")
    n_ref = len(ref_sorted)

    p = (k + 1 - 0.44) / (n_ref + 1 - 0.44 - 0.12)  #Gringorten, I. I. 1963. A plotting rule for extreme probability paper. J. Geophys. Res., 68. No. 3, . 813–814.
    return p

#Conversion probabilité en score standardisé via l'inverse de la CDF normale 
# qui nous donne une valeur plus facile à interpréter en unités d'écart-type par rapport à la médiane.

def empirical_standardize(series, ref_period=None, growing_season_months=None):
    #Score z par CDF empirique. Hors saison de croissance : NaN.
    in_season = growing_season_mask(series.index, growing_season_months)
    ref_sorted = reference_values(series, ref_period, growing_season_months)

    x = series.values.astype("float64")
    valid = np.isfinite(x) & in_season

    standardized = np.full(len(x), np.nan)
    standardized[valid] = norm.ppf(empirical_probability(ref_sorted, x[valid]))

    return pd.Series(standardized, index=series.index,
                     name=f"{series.name}_standardized")
