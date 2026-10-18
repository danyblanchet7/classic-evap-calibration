# -*- coding: utf-8 -*-
"""Proportion de jours dans chaque quadrant SAMI/SSMI, par fenetres de N jours."""

import pandas as pd

# (colonne, libelle, couleur) -- "sec" = indice sous le seuil, "humide" = non sec
QUADRANTS = [
    ("dry_air_wet_soil", "Air sec, sol humide", "#e08214"),
    ("dry_air_dry_soil", "Air sec, sol sec", "#b2182b"),
    ("wet_air_dry_soil", "Air humide, sol sec", "#8c510a"),
    ("wet_air_wet_soil", "Air humide, sol humide", "#4393c3"),
]
QUAD_COLS = [q[0] for q in QUADRANTS]


def get_thresholds(cfg):
    """Seuils de 'sec' : par defaut ceux de la detection d'episodes (-1)."""
    sami_thr = cfg.get("quadrant_sami_threshold", cfg.get("event_sami_threshold", -1.0))
    ssmi_thr = cfg.get("quadrant_ssmi_threshold", cfg.get("event_ssmi_threshold", -1.0))
    return sami_thr, ssmi_thr


def classify_days(sami, ssmi, sami_thr, ssmi_thr):
    """Classe chaque jour (SAMI et SSMI definis) dans un des 4 quadrants.
    Retourne un DataFrame journalier regulier (NaN hors jours valides)."""
    df = pd.concat([sami.rename("SAMI"), ssmi.rename("SSMI")], axis=1).dropna()
    dry_air = df["SAMI"] < sami_thr
    dry_soil = df["SSMI"] < ssmi_thr
    cls = pd.DataFrame({
        "dry_air_wet_soil": dry_air & ~dry_soil,
        "dry_air_dry_soil": dry_air & dry_soil,
        "wet_air_dry_soil": ~dry_air & dry_soil,
        "wet_air_wet_soil": ~dry_air & ~dry_soil,
    }, index=df.index).astype(float)
    cls["SAMI"] = df["SAMI"]
    cls["SSMI"] = df["SSMI"]
    return cls.asfreq("1D")  # jours manquants / hors saison -> NaN


def compute_quadrant_window_fractions(sami, ssmi, cfg):
    """Pour chaque fenetre de `quadrant_window_days` jours (fenetre se
    terminant a la date de l'index), proportion de jours dans chaque quadrant.

    Les fenetres ne traversent jamais l'hors-saison : seules les fenetres
    entierement dans la saison de croissance (>= quadrant_min_valid_days
    jours valides) sont gardees.
    Colonnes : 4 proportions (0-1) + mean_SAMI + mean_SSMI de la fenetre.
    """
    window = cfg.get("quadrant_window_days", 14)
    step = cfg.get("quadrant_window_step_days", 1)
    min_valid = cfg.get("quadrant_min_valid_days", window)
    sami_thr, ssmi_thr = get_thresholds(cfg)

    cls = classify_days(sami, ssmi, sami_thr, ssmi_thr)
    roll = cls.rolling(window, min_periods=min_valid).mean()

    frac = roll[QUAD_COLS].copy()
    frac["mean_SAMI"] = roll["SAMI"]
    frac["mean_SSMI"] = roll["SSMI"]
    frac = frac.dropna(subset=QUAD_COLS)

    if step > 1:  # blocs successifs (step = window -> fenetres disjointes)
        cover_end = cfg.get("quadrant_cover_season_end", True)
        start_month = cfg["growing_season_months"][0]

        def _subsample(g):
            # Blocs alignes sur le 1er jour de la saison (par la DATE, pas par
            # le rang : robuste aux trous), + derniere fenetre disponible pour
            # que la fin de saison / de serie soit toujours representee.
            s0 = pd.Timestamp(g.index[0].year, start_month, 1)
            offset = (g.index - s0).days.to_numpy() - (window - 1)
            sel = g[offset % step == 0]
            if cover_end and (sel.empty or sel.index[-1] != g.index[-1]):
                sel = pd.concat([sel, g.iloc[[-1]]])
            return sel

        frac = frac.groupby(frac.index.year, group_keys=False).apply(_subsample)

    frac.index.name = "window_end"
    return frac


def detect_air_then_soil_sequences(fractions, cfg):
    """Par annee : date du pic de 'air sec, sol humide' (avant le pic de
    'air sec, sol sec'), date du pic 'air sec, sol sec', et decalage.

    air_first_sequence = True si le pic 'air sec, sol humide' precede le pic
    'air sec, sol sec' ET que les deux depassent quadrant_sequence_min_fraction
    (defaut 0.5). Critere heuristique, a ajuster.
    """
    min_f = cfg.get("quadrant_sequence_min_fraction", 0.5)
    cols = ["year", "peak_dry_air_wet_soil", "frac_dry_air_wet_soil",
            "peak_dry_air_dry_soil", "frac_dry_air_dry_soil",
            "lag_days", "air_first_sequence"]
    if fractions.empty:
        return pd.DataFrame(columns=cols)

    rows = []
    for year, g in fractions.groupby(fractions.index.year):
        a, b = g["dry_air_wet_soil"], g["dry_air_dry_soil"]
        t_b = b.idxmax()
        candidates_a = a.loc[:t_b]
        if candidates_a.empty:
            continue
        t_a = candidates_a.idxmax()
        rows.append({
            "year": year,
            "peak_dry_air_wet_soil": t_a.date(),
            "frac_dry_air_wet_soil": round(a.loc[t_a], 3),
            "peak_dry_air_dry_soil": t_b.date(),
            "frac_dry_air_dry_soil": round(b.loc[t_b], 3),
            "lag_days": (t_b - t_a).days,
        })
    out = pd.DataFrame(rows)
    out["air_first_sequence"] = (
        (out["lag_days"] > 0)
        & (out["frac_dry_air_wet_soil"] >= min_f)
        & (out["frac_dry_air_dry_soil"] >= min_f)
    )
    return out.sort_values("frac_dry_air_dry_soil", ascending=False).reset_index(drop=True)


def select_top_windows(fractions, cfg, column="dry_air_dry_soil"):
    """Dates de fin des `quadrant_top_n_windows` fenetres les plus sechement
    composees (proportion maximale de `column`, a egalite : moyenne SAMI+SSMI
    la plus basse), sans chevauchement entre fenetres retenues."""
    n = cfg.get("quadrant_top_n_windows", 6)
    window = cfg.get("quadrant_window_days", 14)

    cand = fractions[fractions[column] > 0].copy()
    cand["_sev"] = cand["mean_SAMI"] + cand["mean_SSMI"]
    cand = cand.sort_values([column, "_sev"], ascending=[False, True])

    chosen = []
    for end in cand.index:
        if all(abs((end - c).days) >= window for c in chosen):
            chosen.append(end)
        if len(chosen) == n:
            break
    return chosen