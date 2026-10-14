
#Calcul du deficit de pression de vapeur (VPD)

import numpy as np


def _saturation_vapour_pressure(T):
     #Pression de vapeur saturante (kPa), formule de Tetens
    return 0.6108 * np.exp(17.27 * T / (T + 237.3))


def compute_vpd(t2m_K, d2m_K):
    #VPD journalier (kPa) a partir des temperatures de l'air et du point de rosee (Kelvin, deja moyennees par jour).
    es_air = _saturation_vapour_pressure(t2m_K - 273.15)
    es_dew = _saturation_vapour_pressure(d2m_K - 273.15)
    vpd = es_air - es_dew

    n_neg = int((vpd < 0).sum())
    if n_neg:
        print(f"  ! {n_neg} VPD negatif(s) mis a 0 (Td > T).")

    return vpd.clip(lower=0).rename("vpd")
