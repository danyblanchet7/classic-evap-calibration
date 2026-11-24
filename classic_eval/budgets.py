"""Bilans : le modèle conserve-t-il l'énergie et l'eau ?

ÉNERGIE
- energy_budget          : table mensuelle (Rn-G, H, LE, résidu, Bowen...) + fermeture du bilan
- plot_energy_closure    : H+LE vs Rn-G (journalier), obs vs CLASSIC
- plot_energy_cumulative : Rn et sa répartition (LE, H, G, résidu) CUMULÉES en MJ m-2,
                           sur toute la période et sur une année choisie

  Méthode de calcul  : moyenne PONDÉRÉE mois x heure
  sur les demi-heures communes obs/sim, pour que les trous des obs (nuit, hiver) ne biaisent
  pas Rn ; le cumul = moyenne pondérée x durée de la période (secondes) / 1e6.
  
  On garde uniquement les demi-heures où toutes les colonnes sont valides : SW↓, SW↑, LW↓, LW↑, H, LE, et G
  s’il est utilisé. Obs et CLASSIC sont ensuite calculés sur ces mêmes timestamps.

Le problème des trous :

Les trous des observations ne sont pas aléatoires : H et LE manquent surtout la nuit (filtrage de turbulence faible)
et en hiver (neige, givre). Une moyenne simple sur les points restants serait donc dominée par les jours d’été en milieu de journée. 
Rn, LE et H en ressortiraient trop élevés, pour les obs et pour la simulation, puisqu’elle est limitée aux mêmes dates.

La pondération mois × heure : 

On découpe le temps en 12 mois × 24 heures = 288 cases. Pour chaque case :

exp = le nombre de demi-heures qu’elle devrait contenir sur la période complète (par exemple janvier à 00 h, pour les 4 années) ;
cnt = le nombre de demi-heures communes réellement valides dedans ;
poids de chaque point = exp / cnt.

Chaque case compte alors à hauteur de sa vraie part de temps, quelle que soit la quantité de données qu’elle contient.
La moyenne est Σ(w·x) / Σw. C’est équivalent à calculer la moyenne de chaque case puis à moyenner les cases selon leur durée réelle.

Exemple : janvier à 00 h a 248 demi-heures attendues mais seulement 20 valides, donc chaque point pèse 12,4. 
Juillet à midi a 248 attendues et 200 valides, donc chaque point pèse 1,24. Les 20 points de nuit d’hiver comptent autant que la case complète,
 et le biais d’échantillonnage disparaît en grande partie.

Les mêmes poids s’appliquent à Rn, LE, H et G. Le résidu = Rn − LE − H − G reste donc cohérent.

-Le cumul :

cumul (MJ m⁻²) = moyenne pondérée (W m⁻²) × durée (s) / 10⁶

La durée est celle des années civiles complètes couvertes : toute la période va du 1er janvier de la première année au 31 décembre de la dernière, et une année choisie dure 365 ou 366 jours.
Exemple : 100 W m⁻² sur un an donnent 100 × 31 536 000 s = environ 3 154 MJ m⁻².

Sur ces demi-heures, on calcule :

Rn = SW↓ - SW↑ + LW↓ - LW↑. (obs et simulé) ;
LE, H et G, avec le même ensemble de dates.

EAU
- water_budget : P - ET - R - dS ; plot_water_budget, plot_water_year (cumuls, dates de neige).
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from . import style

LAMBDA_V = 2.45e6   # J/kg, chaleur latente de vaporisation (approx.)
STEP_S = 1800       # pas de temps demi-horaire (s)


# ÉNERGIE
def _merge_sim(classic, names):
    out = None
    for n in names:
        d = classic[n][["Date", n]].rename(columns={n: "sim_" + n})
        out = d if out is None else out.merge(d, on="Date")
    return out


def energy_budget(obs, classic, cols, g_obs=None, g_sim=None, freq="MS", g_sim_sign=1):
    """Retourne (table périodique, df demi-horaire commun, résumé de fermeture).

    cols : dict cfg.obs_cols (rsd, rsu, rld, rlu, h, le).
    g_obs / g_sim : flux de chaleur du sol obs / CLASSIC (None => G ignoré ; le résidu du
        modèle contient alors G + stockage).
    g_sim_sign : +1 ou -1 pour que G soit POSITIF quand la chaleur entre dans le sol.
    """
    names = ["rsds", "rsus", "rlds", "rlus", "hfss", "hfls"] + ([g_sim] if g_sim else [])
    sim = _merge_sim(classic, names)
    ocols = [cols["rsd"], cols["rsu"], cols["rld"], cols["rlu"], cols["h"], cols["le"]]
    ocols += [g_obs] if g_obs else []
    df = obs[["Date"] + ocols].merge(sim, on="Date")
    n_merged, valid = len(df), df.notna().sum()
    if g_sim:   # G simulé quasi vide => on l'écarte plutôt que de tout perdre
        gcol = "sim_" + g_sim
        ok = df[[c for c in df.columns if c != gcol]].notna().all(axis=1)
        frac = df.loc[ok, gcol].notna().mean() if ok.any() else 0.0
        if frac < 0.5:
            print(f"  ATTENTION : {g_sim} valide à {frac:.1%} seulement -> ignoré "
                  "(vérifier le fichier NetCDF). Bilan calculé sans G simulé.")
            df = df.drop(columns=gcol)
            g_sim = None
    df = df.dropna()
    if df.empty:
        raise ValueError(
            f"Aucun timestamp commun valide : {n_merged} timestamps communs obs/sim, "
            f"mais valeurs valides par colonne :\n{valid.to_string()}\n"
            "=> la colonne à 0 valide est celle à corriger.")

    df["Rn_obs"] = df[cols["rsd"]] - df[cols["rsu"]] + df[cols["rld"]] - df[cols["rlu"]]
    df["Rn_sim"] = df["sim_rsds"] - df["sim_rsus"] + df["sim_rlds"] - df["sim_rlus"]
    df["G_obs"] = df[g_obs] if g_obs else 0.0
    df["G_sim"] = g_sim_sign * df["sim_" + g_sim] if g_sim else 0.0
    df["avail_obs"] = df["Rn_obs"] - df["G_obs"]
    df["avail_sim"] = df["Rn_sim"] - df["G_sim"]
    df["H_obs"], df["LE_obs"] = df[cols["h"]], df[cols["le"]]
    df["H_sim"], df["LE_sim"] = df["sim_hfss"], df["sim_hfls"]

    m = df.set_index("Date").resample(freq).mean(numeric_only=True)
    t = pd.DataFrame(index=m.index)
    for tag in ("obs", "sim"):
        t[f"Rn-G_{tag}"] = m[f"avail_{tag}"]
        t[f"H_{tag}"] = m[f"H_{tag}"]
        t[f"LE_{tag}"] = m[f"LE_{tag}"]
        t[f"Residu_{tag}"] = m[f"avail_{tag}"] - m[f"H_{tag}"] - m[f"LE_{tag}"]
        t[f"EBR_{tag}"] = (m[f"H_{tag}"] + m[f"LE_{tag}"]) / m[f"avail_{tag}"]
        t[f"Bowen_{tag}"] = m[f"H_{tag}"] / m[f"LE_{tag}"]
        t[f"EF_{tag}"] = m[f"LE_{tag}"] / (m[f"H_{tag}"] + m[f"LE_{tag}"])
    t = t.replace([np.inf, -np.inf], np.nan)

    daily = df.set_index("Date").resample("1D").mean(numeric_only=True).dropna()
    summary = {}
    for tag in ("obs", "sim"):
        x = daily[f"avail_{tag}"].values
        y = (daily[f"H_{tag}"] + daily[f"LE_{tag}"]).values
        slope, intercept = np.polyfit(x, y, 1)
        summary[tag] = {"slope": slope, "intercept": intercept,
                        "EBR_global": y.sum() / x.sum(), "n_days": len(x)}
    summary["sim"]["g_used"] = bool(g_sim)
    return t, df, summary


def plot_energy_closure(df, summary, output_path, name="energy_closure.png"):
    daily = df.set_index("Date").resample("1D").mean(numeric_only=True).dropna()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharex=True, sharey=True)
    for ax, tag, color in zip(axes, ("obs", "sim"), (style.OBS_COLOR, style.SIM_COLOR)):
        x = daily[f"avail_{tag}"]
        y = daily[f"H_{tag}"] + daily[f"LE_{tag}"]
        ax.scatter(x, y, s=6, alpha=0.4, color=color)
        lim = [min(x.min(), y.min()), max(x.max(), y.max())]
        ax.plot(lim, lim, "--", color="gray", lw=1)                 # droite 1:1
        sm = summary[tag]
        ax.plot(lim, [sm["slope"] * v + sm["intercept"] for v in lim], color=color)
        ax.set_title(f"{'Obs' if tag == 'obs' else 'CLASSIC'} | pente {sm['slope']:.2f}, "
                     f"EBR {sm['EBR_global']:.2f}")
        ax.set_xlabel("Rn - G (W m-2)")
    axes[0].set_ylabel("H + LE (W m-2)")
    fig.tight_layout()
    return style.save(fig, os.path.join(output_path, name))


# ------------------------------------------- CUMUL ET RÉPARTITION DE Rn
def _expected_range(d, years=None):
    """Série COMPLÈTE de demi-heures attendues (années civiles entières)."""
    if years is not None:
        start, end = pd.Timestamp(years[0], 1, 1), pd.Timestamp(years[1], 12, 31, 23, 30)
    else:
        start = pd.Timestamp(d["Date"].min().year, 1, 1)
        end = pd.Timestamp(d["Date"].max().year, 12, 31, 23, 30)
    return pd.date_range(start, end, freq="30min")


def _cell_weights(d, full):
    """Poids par demi-heure pour corriger le biais d'échantillonnage mois x heure.

    Poids = (nb de demi-heures de la case (mois, heure) dans la série COMPLÈTE) /
            (nb de demi-heures communes obs/sim dans cette case). `coverage` = part de la
    série complète représentée par les cases qui ont des données.
    """
    exp = pd.Series(1, index=full).groupby([full.month, full.hour]).sum()
    idx = pd.MultiIndex.from_arrays([d["Date"].dt.month, d["Date"].dt.hour])
    cnt = d.groupby([d["Date"].dt.month, d["Date"].dt.hour]).size()
    w = exp.reindex(idx).values / cnt.reindex(idx).values
    return w, float(exp.reindex(cnt.index).sum() / exp.sum())


def energy_totals(df, years=None, weighted=True):
    """Rn, LE, H, G, résidu : moyennes (W m-2) ET cumuls (MJ m-2) sur la période.

    years=None : toutes les années communes ; years=(2021, 2021) : une année.
    cumul = moyenne (pondérée mois x heure si weighted) x durée de la période (s) / 1e6.
    """
    d = df if years is None else df[df["Date"].dt.year.between(*years)]
    if d.empty:
        raise ValueError(f"pas de données communes pour {years}")
    full = _expected_range(d, years)
    w, cov = _cell_weights(d, full) if weighted else (np.ones(len(d)), 1.0)
    duration = len(full) * STEP_S
    out = {"duration_days": duration / 86400}
    for tag in ("obs", "sim"):
        mean = {k: float(np.average(d[f"{k}_{tag}"].values, weights=w)) for k in ("Rn", "LE", "H", "G")}
        mean["Residu"] = mean["Rn"] - mean["LE"] - mean["H"] - mean["G"]
        out[tag] = {"mean": mean, "total": {k: v * duration / 1e6 for k, v in mean.items()},
                    "n": len(d), "coverage": cov}
    return out


def plot_energy_cumulative(df, output_path, g_available=True, weighted=True, periods=None,
                           g_obs_available=False, filename="energy_cumulative.png", suptitle=None):
    """Barres empilées : Rn cumulé (ligne pointillée) réparti en LE, H, G et part non expliquée.

    periods : liste de (titre, years) ; years=None = toute la période, ou (a, b).
    Retourne le tableau des cumuls (DataFrame).
    Obs : LE, H, G si g_obs_available, sinon 'non mesuré (G + résidu)'. CLASSIC : LE, H, G (si dispo),
    résidu du modèle.
    """
    colors = {"LE": "#4daf4a", "H": "#f28e2b", "G": "#8c6d31",
              "Non mesuré (G + résidu)": "#b8b8b8", "Résidu": "#d9d9d9"}
    hatches = {"Non mesuré (G + résidu)": "///", "Résidu": "///"}
    periods = periods or [("Toutes les années", None)]
    fig, axes = plt.subplots(1, len(periods), figsize=(5.4 * len(periods), 5.4), sharey=False,
                             squeeze=False)
    seen, rows = [], []
    for ax, (title, yrs) in zip(axes.ravel(), periods):
        try:
            res = energy_totals(df, yrs, weighted)
        except ValueError:
            ax.set_title(f"{title}\n(pas de données communes)")
            ax.axis("off")
            continue
        o, v = res["obs"]["total"], res["sim"]["total"]
        bars = {
            "Obs": (o["Rn"], style.OBS_COLOR,
                    [("LE", o["LE"]), ("H", o["H"])] + ([("G", o["G"])] if g_obs_available else [])
                    + [("Résidu" if g_obs_available else "Non mesuré (G + résidu)",
                        o["Rn"] - o["LE"] - o["H"] - (o["G"] if g_obs_available else 0))]),
            "CLASSIC": (v["Rn"], style.SIM_COLOR,
                        [("LE", v["LE"]), ("H", v["H"])] + ([("G", v["G"])] if g_available else [])
                        + [("Résidu" if g_available else "Non mesuré (G + résidu)",
                            v["Rn"] - v["LE"] - v["H"] - (v["G"] if g_available else 0))]),
        }
        for i, (name, (rn, edge, segs)) in enumerate(bars.items()):
            up = dn = 0.0
            for lab, val in segs:
                bottom = up if val >= 0 else dn
                ax.bar(i, val, bottom=bottom, width=0.55, color=colors[lab], edgecolor="white",
                       linewidth=1.2, hatch=hatches.get(lab))
                if abs(val) > 0.05 * abs(rn):
                    ax.text(i, bottom + val / 2, f"{val:.0f}", ha="center", va="center",
                            color="white" if lab in ("LE", "H", "G") else "#333333",
                            fontsize=10, fontweight="bold")
                up, dn = (up + val, dn) if val >= 0 else (up, dn + val)
                if lab not in seen:
                    seen.append(lab)
            ax.hlines(rn, i - 0.38, i + 0.38, colors="black", linestyles="--", lw=1.8)
            ax.text(i + 0.4, rn, f" Rn {rn:.0f}", va="center", fontsize=9)
            lemh = dict(segs)["LE"] + dict(segs)["H"]
            ax.text(i, -0.07, f"(H+LE)/Rn = {lemh / rn:.2f}", transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=9, color="#555555")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Obs", "CLASSIC"], fontsize=11)
        for tick, c in zip(ax.get_xticklabels(), (style.OBS_COLOR, style.SIM_COLOR)):
            tick.set_color(c)
        ax.set_xlim(-0.6, 1.9)
        ax.set_title(f"{title}  ({res['duration_days']:.0f} j)", fontsize=12)
        ax.axhline(0, color="#444444", lw=0.8)
        ax.set_ylabel("Énergie cumulée (MJ m$^{-2}$)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", alpha=0.25)
        ax.grid(axis="x", visible=False)
        for src in ("obs", "sim"):
            rows.append({"Période": title, "Source": src, "Durée_j": res["duration_days"],
                         **{f"{k}_Wm2": x for k, x in res[src]["mean"].items()},
                         **{f"{k}_MJm2": x for k, x in res[src]["total"].items()},
                         "couverture": res[src]["coverage"]})
    order = [lab for lab in colors if lab in seen]
    handles = [plt.Rectangle((0, 0), 1, 1, fc=colors[lab], ec="white", hatch=hatches.get(lab))
               for lab in order] + [plt.Line2D([0], [0], color="gray", ls="--")]
    fig.legend(handles, order + ["Rn cumulé"], loc="lower center", ncol=len(order) + 1,
               fontsize=9, frameon=False)
    fig.suptitle(suptitle or "Rn cumulé et répartition de l'énergie", fontsize=13)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    style.save(fig, os.path.join(output_path, filename), dpi=170)
    return pd.DataFrame(rows)


# EAU
def _to_daily(df, col, how="mean"):
    s = df.set_index("Date")[col].resample("1D")
    return s.mean() if how == "mean" else s.last()


def load_total_soil_water(classic_dir, filename="mrsol_daily.nc"):
    """Eau totale du sol (kg m-2) = somme de TOUTES les couches de mrsol (brut).

    mrso n'existe qu'en mensuel ; ceci donne un stock journalier pour le bilan d'eau.
    Retourne un DataFrame Date / mrso (même format que le dict `classic`).
    """
    import netCDF4 as nc
    from .loaders import read_time
    ds = nc.Dataset(os.path.join(classic_dir, filename))
    try:
        raw = ds.variables["mrsol"][:, :, 0, 0]          # (time, layer)
        dates = read_time(ds)
    finally:
        ds.close()
    return pd.DataFrame({"Date": dates, "mrso": np.ma.filled(raw, np.nan).sum(axis=1)})


def water_budget(classic, p="pr", et="evspsbl", runoff=("mrro",),
                 storages=("mrso", "snw"), freq="MS"):
    """Bilan d'eau  P - ET - R - dS = résidu  (kg m-2, cumul par période).

    Flux CLASSIC en kg m-2 s-1 -> x86400. Si `et` est absent, ET = hfls / lambda.
    storages : variables d'état en kg m-2 (sol total, neige, interception...).
    """
    need = [p, *runoff, *storages] + ([et] if et in classic else [])
    missing = [v for v in need if v not in classic]
    if missing:
        raise KeyError(f"Variables CLASSIC manquantes pour le bilan d'eau : {missing}. "
                       "Ajouter dans cfg.classic_files.")
    P = _to_daily(classic[p], p) * 86400
    if et in classic:
        ET = _to_daily(classic[et], et) * 86400
    else:
        ET = _to_daily(classic["hfls"], "hfls") / LAMBDA_V * 86400
    R = sum(_to_daily(classic[r], r) for r in runoff) * 86400
    S = sum(_to_daily(classic[s], s, "last") for s in storages)
    d = pd.concat({"P": P, "ET": ET, "R": R, "dS": S.diff()}, axis=1).dropna()
    d["Residu"] = d["P"] - d["ET"] - d["R"] - d["dS"]
    t = d.resample(freq).sum()
    t["ET/P"] = t["ET"] / t["P"].replace(0, np.nan)
    t["R/P"] = t["R"] / t["P"].replace(0, np.nan)
    t["Fermeture"] = 1 - t["Residu"].abs() / t["P"].replace(0, np.nan)
    return t, d


def plot_water_budget(daily, output_path):
    """Cumuls P, ET, R, résidu (CLASSIC seul : couleurs par composante)."""
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for c, col in (("P", "tab:purple"), ("ET", "tab:green"), ("R", "tab:brown"), ("Residu", "tab:red")):
        ax.plot(daily.index, daily[c].cumsum(), label=f"{c} cumulé", color=col)
    ax.set_ylabel("kg m-2")
    ax.set_title("Bilan d'eau CLASSIC (cumuls)")
    ax.legend()
    fig.tight_layout()
    return style.save(fig, os.path.join(output_path, "water_budget.png"))


# ------------------------------------- CUMUL SUR ANNÉE HYDROLOGIQUE (oct -> sept)
def plot_water_year(daily, swe, output_path, years=(2016, 2017), thr=1.0,
                    obs_snow_csv=None, sites=("LG", "CAN"), thr_cm=2.0, min_days=5,
                    snd=None, sim_basis="swe", melt_frac=0.9):
    """P, O (ruissellement), E (ET) cumulés sur l'année hydrologique, par année,
    avec les dates de neige : CLASSIC (gris) et, si obs_snow_csv est fourni, obs (vert).

    daily : DataFrame journalier de water_budget() (colonnes P, ET, R, dS, Residu)
    swe   : DataFrame Date/snw (kg m-2) de CLASSIC
    years : années de DÉBUT (2023 -> 1er oct 2023 au 30 sept 2024)
    obs_snow_csv : CSV de neige (colonnes time, site, snow_depth en cm) -> dates obs
    sim_basis : "swe" (CLASSIC par SWE, seuil thr mm) ou "snd" (CLASSIC par hauteur,
                mêmes règles/seuil thr_cm que les obs, pour comparer à armes égales ;
                nécessite snd = DataFrame Date/snd en m)
    Règles : accumulation = 1re séquence >= min_days jours > seuil ; début de fonte =
    dernier jour où la neige lissée est >= melt_frac x son max (début de la décrue
    finale) ; fin de fonte = dernier jour avec neige.
    """
    import matplotlib.dates as mdates
    from matplotlib.lines import Line2D
    from .temporal import snow_key_dates, load_obs_snow_sites

    swe_d = swe.set_index("Date")["snw"].resample("1D").mean()
    swe_d.index = swe_d.index.normalize()
    snd_d = None
    if snd is not None:
        snd_d = snd.set_index("Date")["snd"].resample("1D").mean() * 100
        snd_d.index = snd_d.index.normalize()

    ref0 = pd.Timestamp(2000, 10, 1)            # axe commun oct -> sept
    styles = ["-", ":", "--", "-."]
    keys = (("accumulation", "Début accumulation"), ("melt_start", "Début fonte"),
            ("melt_end", "Fin de fonte"))
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    rows, legend, used_obs, used_sim = [], [], False, False
    for k, hy in enumerate(years):
        ls = styles[k % len(styles)]
        t0, t1 = pd.Timestamp(hy, 10, 1), pd.Timestamp(hy + 1, 9, 30)
        days = pd.date_range(t0, t1, freq="D")
        sub = daily[(daily.index >= t0) & (daily.index <= t1)].reindex(days)
        if sub["P"].notna().mean() < 0.9:
            print(f"  année hydrologique {hy}-{hy + 1} : données insuffisantes, ignorée")
            continue
        x = ref0 + (sub.index - t0)
        tot = {}
        for var, col, lab in (("P", "tab:purple", "P"), ("R", "tab:brown", "O"), ("ET", "tab:green", "E")):
            cum = sub[var].fillna(0).cumsum()
            ax.plot(x, cum, color=col, ls=ls, lw=1.8)
            tot[lab] = float(cum.iloc[-1])
        label = f"{hy}-{hy + 1}"
        legend += [Line2D([0], [0], color=c, ls=ls, lw=1.8, label=f"{n} ({label})")
                   for n, c in (("P", "tab:purple"), ("O", "tab:brown"), ("E", "tab:green"))]

        # dates de neige CLASSIC
        if sim_basis == "snd" and snd_d is not None:
            ser, thr_s = snd_d.reindex(days), thr_cm
        else:
            ser, thr_s = swe_d.reindex(days), thr
        sim_d = snow_key_dates(ser, thr_s, min_days, melt_frac) if ser.notna().mean() >= 0.9 else None
        # dates de neige obs (CSV)
        obs_d = None
        if obs_snow_csv:
            o = load_obs_snow_sites(obs_snow_csv, sites, t0, t1).reindex(days)["mean"]
            if o.notna().sum() >= 30:
                obs_d = snow_key_dates(o, thr_cm, min_days, melt_frac)
            else:
                print(f"  {label} : pas d'observation de neige dans le CSV pour cette année.")

        for d, color, tag, ha in ((sim_d, style.SIM_COLOR, "CLASSIC", "right"),
                                  (obs_d, style.OBS_COLOR, "Obs", "left")):
            if not d:
                continue
            used_sim |= tag == "CLASSIC"
            used_obs |= tag == "Obs"
            for key, txt in keys:
                if pd.isna(d[key]):
                    continue
                xv = ref0 + (d[key] - t0)
                ax.axvline(xv, color=color, ls=ls if tag == "CLASSIC" else "--", lw=1.3)
                ax.text(xv, 0.99, f"{txt} {tag} · {pd.Timestamp(d[key]):%d %b}"
                        + (f" ({label})" if len(years) > 1 else ""),
                        transform=ax.get_xaxis_transform(), rotation=90, va="top", ha=ha,
                        fontsize=7.5, color=color,
                        bbox=dict(fc="white", ec="none", alpha=0.75, pad=1))
        row = {"Année hydrologique": label, **tot,
               "dS": float(sub["dS"].fillna(0).sum()),
               "Résidu": float(sub["Residu"].fillna(0).sum())}
        for tag, d in (("classic", sim_d), ("obs", obs_d)):
            if d:
                for key, _ in keys:
                    row[f"{key}_{tag}"] = d[key].date() if pd.notna(d[key]) else None
        if sim_d and obs_d:
            for key, _ in keys:
                if pd.notna(sim_d[key]) and pd.notna(obs_d[key]):
                    row[f"{key}_ecart_j"] = (sim_d[key] - obs_d[key]).days
        rows.append(row)

    if used_sim:
        base = "swe" if sim_basis != "snd" or snd_d is None else "hauteur"
        legend.append(Line2D([0], [0], color=style.SIM_COLOR, ls=":", label=f"Dates neige CLASSIC ({base})"))
    if used_obs:
        legend.append(Line2D([0], [0], color=style.OBS_COLOR, ls="--", label="Dates neige obs (CSV)"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_xlim(ref0, ref0 + pd.Timedelta(days=364))
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Eau cumulée (mm)")
    ax.grid(alpha=0.3)
    ax.legend(handles=legend, loc="center right", bbox_to_anchor=(0.99, 0.56),
              fontsize=8, frameon=True)
    fig.tight_layout()
    suffix = "_".join(str(y) for y in years)
    style.save(fig, os.path.join(output_path, f"water_budget_hydro_year_{suffix}.png"), dpi=170)
    return pd.DataFrame(rows)
