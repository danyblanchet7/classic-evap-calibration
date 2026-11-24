"""Évaluation dynamique / temporelle : le timing est-il bon ?

- cycle diurne (par saison) + déphasage
- dates de début/fin de neige (année hydrologique) + vérification détaillée d'une année
- phénologie GPP (début / fin / longueur de saison)
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from . import style
from .metrics import phase_shift

SEASONS = {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "JJA": [6, 7, 8], "SON": [9, 10, 11]}


# cycle diurne
def diurnal_cycle(perf, months=None):
    d = perf.copy()
    if months is not None:
        d = d[d["Date"].dt.month.isin(months)]
    d["tod"] = d["Date"].dt.hour + d["Date"].dt.minute / 60
    return d.groupby("tod")[["OBS", "SIM"]].mean()


def plot_diurnal(perf, variable, units, output_path):
    """4 panneaux (DJF/MAM/JJA/SON). Retourne un DataFrame de déphasages (h)."""
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8), sharey=True)
    rows = []
    for ax, (name, months) in zip(axes, SEASONS.items()):
        g = diurnal_cycle(perf, months)
        if len(g) < 8:
            ax.set_title(f"{name} (pas de données)")
            continue
        ax.plot(g.index, g["OBS"], color=style.OBS_COLOR, label=style.OBS_LABEL)
        ax.plot(g.index, g["SIM"], color=style.SIM_COLOR, label=style.SIM_LABEL)
        step = float(np.median(np.diff(g.index.values)))
        gi = g.interpolate(limit_direction="both")
        lag = phase_shift(gi["OBS"].values, gi["SIM"].values, step_hours=step,
                          circular=True)
        peak_o, peak_s = g["OBS"].idxmax(), g["SIM"].idxmax()
        rows.append({"Variable": variable, "Season": name, "Shift_h": lag,
                     "Peak_obs_h": peak_o, "Peak_sim_h": peak_s})
        ax.set_title(f"{name} | décalage {lag:+.1f} h")
        ax.set_xlabel("Heure")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"{variable} ({units})")
    axes[0].legend()
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, f"diurnal_{variable}.png"))
    return pd.DataFrame(rows)



def _runs(mask):
    """Liste (début, fin, longueur) des séquences True d'une Series booléenne."""
    grp = (mask != mask.shift()).cumsum()
    out = []
    for _, s in mask.groupby(grp):
        if s.iloc[0]:
            out.append((s.index[0], s.index[-1], len(s)))
    return out


def _bounds(mask, min_days):
    runs = [r for r in _runs(mask) if r[2] >= min_days]
    if not runs:
        return pd.NaT, pd.NaT, 0
    return runs[0][0], runs[-1][1], int(mask.sum())


def compare_tables(t_obs, t_sim):
    """Fusionne deux tables (index = année) -> colonnes *_obs, *_sim, *_diff (sim-obs)."""
    t = t_obs.join(t_sim, lsuffix="_obs", rsuffix="_sim", how="inner")
    for k in ("start_doy", "end_doy", "length"):
        t[f"{k}_diff"] = t[f"{k}_sim"] - t[f"{k}_obs"]
    return t.dropna(subset=["start_doy_obs", "start_doy_sim"], how="all")


def plot_event_comparison(table, name, output_path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, k, lab in zip(axes, ("start_doy", "end_doy"), ("Début", "Fin")):
        x, y = table[f"{k}_obs"], table[f"{k}_sim"]
        ax.scatter(x, y, color="k")
        for yr in table.index:
            ax.annotate(str(yr), (x[yr], y[yr]), fontsize=8)
        lo = np.nanmin([x.min(), y.min()]) - 10
        hi = np.nanmax([x.max(), y.max()]) + 10
        ax.plot([lo, hi], [lo, hi], "--", color="gray")
        ax.set_xlabel("Obs (jour)")
        ax.set_ylabel("CLASSIC (jour)")
        ax.set_title(f"{name} - {lab}")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, f"events_{name}.png"))


# NEIGE
def load_obs_snow_daily(csv_path, sites=("LG", "CAN"), start=None, end=None):
    """Moyenne journalière (cm) de la hauteur de neige des sites. Series indexée par date."""
    return load_obs_snow_sites(csv_path, sites, start, end)["mean"]


def snow_season_table(daily_cm, threshold_cm=2.0, min_days=5, hydro_start_month=8,
                      min_coverage=0.8):
    """Début / fin / durée de la saison de neige par année hydrologique (août->juillet).

    start_doy / end_doy = jours depuis le 1er août.
    Année avec trop de jours manquants (< min_coverage) ignorée.
    """
    s = daily_cm.copy()
    s.index = pd.to_datetime(s.index).normalize()
    hy = s.index.year + (s.index.month >= hydro_start_month).astype(int)
    rows = {}
    for y in np.unique(hy):
        sub = s[hy == y]
        if sub.notna().mean() < min_coverage or len(sub) < 330:
            continue
        mask = (sub > threshold_cm).fillna(False)
        start, end, length = _bounds(mask, min_days)
        ref = pd.Timestamp(int(y) - 1, hydro_start_month, 1)
        rows[int(y)] = {
            "start": start, "end": end,
            "start_doy": (start - ref).days if pd.notna(start) else np.nan,
            "end_doy": (end - ref).days if pd.notna(end) else np.nan,
            "length": length,
        }
    return pd.DataFrame(rows).T if rows else pd.DataFrame(
        columns=["start", "end", "start_doy", "end_doy", "length"])


# PHÉNOLOGIE
def gpp_phenology_table(daily, frac=0.15, smooth=7, min_days=5, min_coverage=0.8):
    """Début / fin / longueur de la saison de croissance (GPP lissée > seuil).

    Seuil par année = p5 + frac * (p95 - p5). start_doy / end_doy = jour de l'année.
    """
    s = daily.copy()
    s.index = pd.to_datetime(s.index).normalize()
    rows = {}
    for y, sub in s.groupby(s.index.year):
        if sub.notna().mean() < min_coverage or len(sub) < 330:
            continue
        sm = sub.rolling(smooth, center=True, min_periods=max(1, smooth // 2)).mean()
        p5, p95 = sm.quantile(0.05), sm.quantile(0.95)
        thr = p5 + frac * (p95 - p5)
        mask = (sm > thr).fillna(False)
        start, end, length = _bounds(mask, min_days)
        rows[int(y)] = {
            "start": start, "end": end,
            "start_doy": start.dayofyear if pd.notna(start) else np.nan,
            "end_doy": end.dayofyear if pd.notna(end) else np.nan,
            "length": length,
        }
    return pd.DataFrame(rows).T if rows else pd.DataFrame(
        columns=["start", "end", "start_doy", "end_doy", "length"])


# VÉRIFICATION DES DATES DE NEIGE (OBS vs CLASSIC)
def load_obs_snow_sites(csv_path, sites=("LG", "CAN"), start=None, end=None):
    """Hauteur de neige obs (cm), moyenne journalière par site + moyenne des sites.

    Retourne un DataFrame (index = jours) avec une colonne par site et 'mean'.
    """
    obs = pd.read_csv(csv_path)
    obs["Date"] = pd.to_datetime(obs["time"], format="mixed")
    cols = {}
    for s in sites:
        o = obs[obs["site"] == s]
        cols[s] = o.set_index("Date")["snow_depth"].resample("1D").mean()
    df = pd.DataFrame(cols)
    df.index = df.index.normalize()
    df["mean"] = df[list(sites)].mean(axis=1)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


def snow_key_dates(series, thr=2.0, min_days=5, melt_frac=0.9, smooth=5):
    """Dates clés à partir d'une série journalière de neige (cm ou mm de SWE).

    accumulation : 1er jour de la 1re séquence >= min_days jours avec valeur > thr
    melt_end     : dernier jour avec neige (fin de séquence >= min_days)
    melt_start   : DERNIER jour où la neige (lissée sur `smooth` jours) est encore
                   >= melt_frac x son maximum saisonnier, i.e. le début de la décrue
                   finale. Évite qu'un pic précoce (tassement, plateau hivernal)
                   fixe un début de fonte en janvier. melt_frac=None => date du maximum.
    max_date     : date du maximum (lissé), donnée à titre de diagnostic.
    """
    s = series.copy()
    s.index = pd.to_datetime(s.index).normalize()
    first, last, n = _bounds((s > thr).fillna(False), min_days)
    out = {"accumulation": first, "melt_start": pd.NaT, "melt_end": last,
           "max_date": pd.NaT, "max": np.nan, "jours_neige": n,
           "couverture": float(s.notna().mean())}
    if pd.notna(first) and s.notna().any():
        win = s.loc[first:last]
        sm = (win.rolling(smooth, center=True, min_periods=1).mean()
              if smooth and smooth > 1 else win)
        peak = sm.max()
        out["max"] = float(s.max())
        out["max_date"] = sm.idxmax()
        out["melt_start"] = (sm.idxmax() if melt_frac is None
                             else sm[sm >= melt_frac * peak].index.max())
    return out


def verify_snow_dates(obs_csv, classic, output_path, hy=2023, sites=("LG", "CAN"),
                      thr_cm=2.0, min_days=5, swe_thr=1.0, melt_frac=0.9):
    """Compare les dates d'accumulation / début de fonte / fin de fonte obs vs CLASSIC
    pour UNE année hydrologique (1er oct hy -> 30 sept hy+1) et trace la figure.

    Obs et CLASSIC (snd) utilisent les mêmes règles sur la hauteur de neige (cm) ;
    CLASSIC par SWE (snw) est ajouté à titre de référence.
    Retourne le tableau des dates (CSV déjà écrit).
    """
    import matplotlib.dates as mdates
    t0, t1 = pd.Timestamp(hy, 10, 1), pd.Timestamp(hy + 1, 9, 30)
    days = pd.date_range(t0, t1, freq="D")

    obs = load_obs_snow_sites(obs_csv, sites, t0, t1).reindex(days)
    if obs["mean"].notna().sum() == 0:
        raise ValueError(f"Aucune observation de neige entre {t0.date()} et {t1.date()} "
                         "(le CSV ne couvre peut-être pas cette année hydrologique).")
    snd = classic["snd"].set_index("Date")["snd"].resample("1D").mean() * 100
    snd.index = snd.index.normalize()
    snd = snd.reindex(days)
    swe = None
    if "snw" in classic:
        swe = classic["snw"].set_index("Date")["snw"].resample("1D").mean()
        swe.index = swe.index.normalize()
        swe = swe.reindex(days)

    sources = {f"Obs {s}": (obs[s], thr_cm) for s in sites}
    sources["Obs moyenne"] = (obs["mean"], thr_cm)
    sources["CLASSIC (hauteur)"] = (snd, thr_cm)
    if swe is not None:
        sources["CLASSIC (SWE)"] = (swe, swe_thr)

    rows = {}
    for name, (ser, thr) in sources.items():
        rows[name] = snow_key_dates(ser, thr, min_days, melt_frac)
    table = pd.DataFrame(rows).T
    ref = table.loc["Obs moyenne"]
    for k in ("accumulation", "melt_start", "melt_end"):
        table[f"{k}_ecart_j"] = (pd.to_datetime(table[k]) - pd.to_datetime(ref[k])).dt.days
    label = f"{hy}-{hy + 1}"
    table.to_csv(os.path.join(output_path, f"snow_dates_check_{label}.csv"), encoding="utf-8-sig")

    # figure
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for i, s in enumerate(sites):            
        ax.plot(days, obs[s], color=style.OBS_GREYS[i % len(style.OBS_GREYS)], lw=1, label=f"Obs {s}")
    ax.plot(days, obs["mean"], color=style.OBS_COLOR, lw=2, label="Obs moyenne")
    ax.plot(days, snd, color=style.SIM_COLOR, lw=1.5, label=style.SIM_LABEL)

    ymax = np.nanmax([np.nanmax(obs["mean"]), np.nanmax(snd)]) if len(days) else 1
    ax.set_ylim(0, ymax * 1.12)
    for who, color, ls, ha in (("Obs moyenne", style.OBS_COLOR, "--", "right"),
                               ("CLASSIC (hauteur)", style.SIM_COLOR, ":", "left")):
        for key, txt in (("accumulation", "Début accumulation"),
                         ("melt_start", "Début fonte"),
                         ("melt_end", "Fin de fonte")):
            d = table.loc[who, key]
            if pd.isna(d):
                continue
            ax.axvline(d, color=color, ls=ls, lw=1.3)
            ax.text(d, 0.99, f"{txt} · {pd.Timestamp(d):%d %b}",
                    transform=ax.get_xaxis_transform(), rotation=90, va="top", ha=ha,
                    fontsize=7.5, color=color,
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=1))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_xlim(t0, t1)
    ax.set_ylabel("Hauteur de neige (cm)")
    ax.set_title(f"Vérification des dates de neige - année hydrologique {label}")
    ax.grid(alpha=0.3)
    h, l = ax.get_legend_handles_labels()
    h += [plt.Line2D([0], [0], color=style.OBS_COLOR, ls="--"), plt.Line2D([0], [0], color=style.SIM_COLOR, ls=":")]
    l += ["Dates clés obs (gris)", "Dates clés CLASSIC (bleu)"]
    ax.legend(h, l, loc="center right", fontsize=9)
    fig.tight_layout()
    style.save(fig, os.path.join(output_path, f"snow_dates_check_{label}.png"), dpi=170)
    return table

