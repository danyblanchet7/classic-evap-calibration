# -*- coding: utf-8 -*-
"""Detection des episodes de secheresse composee (air + sol)."""

import pandas as pd

EVENT_COLUMNS = [
    "start", "end", "duration_days", "mean_SAMI", "mean_SSMI",
    "min_SAMI", "min_SSMI", "severity",
]


def _empty():
    return pd.DataFrame(columns=EVENT_COLUMNS)


def detect_compound_dry_events(sami, ssmi, cfg):
    """Episodes ou les moyennes glissantes de SAMI ET SSMI sont sous leurs
    seuils, regroupes en tolerant de courtes interruptions, puis filtres
    par duree minimale. Tri : du plus severe au moins severe."""
    window = cfg["event_window_days"]
    sami_thr = cfg["event_sami_threshold"]
    ssmi_thr = cfg["event_ssmi_threshold"]
    min_duration = cfg["event_min_duration_days"]
    max_gap = cfg["event_max_gap_days"]

    df = pd.concat([sami.rename("SAMI"), ssmi.rename("SSMI")], axis=1).dropna()
    if len(df) < window:
        print(f"  ! Pas assez de donnees ({len(df)} j) pour une fenetre de {window} j.")
        return _empty()

    roll_sami = df["SAMI"].rolling(window, min_periods=window).mean()
    roll_ssmi = df["SSMI"].rolling(window, min_periods=window).mean()
    flagged = df.index[(roll_sami < sami_thr) & (roll_ssmi < ssmi_thr)]

    if len(flagged) == 0:
        print(f"  Aucun jour sous les seuils (SAMI < {sami_thr}, SSMI < {ssmi_thr}).")
        return _empty()

    # Regroupement en episodes continus
    episodes, ep_start, ep_prev = [], flagged[0], flagged[0]
    for d in flagged[1:]:
        if (d - ep_prev).days > max_gap + 1:
            episodes.append((ep_start, ep_prev))
            ep_start = d
        ep_prev = d
    episodes.append((ep_start, ep_prev))

    rows = []
    for start, end in episodes:
        duration = (end - start).days + 1
        if duration < min_duration:
            continue
        w = df.loc[start:end]
        rows.append({
            "start": start.date(),
            "end": end.date(),
            "duration_days": duration,
            "mean_SAMI": round(w["SAMI"].mean(), 3),
            "mean_SSMI": round(w["SSMI"].mean(), 3),
            "min_SAMI": round(w["SAMI"].min(), 3),
            "min_SSMI": round(w["SSMI"].min(), 3),
            "severity": round(w["SAMI"].mean() + w["SSMI"].mean(), 3),
        })

    if not rows:
        print(f"  Aucun episode d'au moins {min_duration} j apres regroupement.")
        return _empty()

    return pd.DataFrame(rows, columns=EVENT_COLUMNS).sort_values("severity").reset_index(drop=True)
