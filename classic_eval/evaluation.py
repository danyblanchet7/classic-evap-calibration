"""Évaluation quantitative variable par variable (étapes 01, 02, 03 et 05).

- annual_overview : moyenne annuelle (cycle mensuel) de toutes les variables, une figure
- example_year    : une année complète (moyennes journalières), toutes les variables
- six_panel       : 6 graphiques par variable = moyenne annuelle + les 5 périodes choisies
- metrics_all_years : tableau de métriques journalières (toutes années) + IAV
"""
import math
import pandas as pd
import matplotlib.pyplot as plt
from . import style
from .metrics import calculate_metrics, iav
from .prepare import align, is_daily

MONTHS = list("JFMAMJJASOND")


def metrics_text(m, units):
    if "RMSE" not in m:
        return "données insuffisantes"
    return f"r={m['r']:.2f} · RMSE={m['RMSE']:.3g} · biais={m['Bias']:+.3g} {units}"


# cycle annuel
def annual_cycle(perf):
    """Moyenne et écart-type INTERANNUEL de la moyenne mensuelle (index = mois 1..12)."""
    monthly = perf.set_index("Date")[["OBS", "SIM"]].resample("MS").mean().dropna()
    g = monthly.groupby(monthly.index.month)
    return g.mean(), g.std()


def draw_annual_cycle(ax, perf):
    mean, std = annual_cycle(perf)
    for key, color, label in (("OBS", style.OBS_COLOR, style.OBS_LABEL),
                              ("SIM", style.SIM_COLOR, style.SIM_LABEL)):
        ax.plot(mean.index, mean[key], color=color, marker="o", ms=4, label=label)
        ax.fill_between(mean.index, mean[key] - std[key], mean[key] + std[key],
                        color=color, alpha=0.12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTHS)


def _no_data(ax, title):
    ax.text(0.5, 0.5, "pas de données communes", ha="center", va="center",
            transform=ax.transAxes, color="gray")
    ax.set_title(title, fontsize=9)


#  01 : moyenne annuelle
def annual_overview(ctx, variables, out_dir, name="annual_mean_all_variables.png"):
    """Grille de cycles annuels moyens (± écart-type interannuel), un panneau par variable."""
    variables = [v for v in variables if ctx.available(v)]
    if not variables:
        raise ValueError("aucune variable disponible")
    ncols = 3
    nrows = math.ceil(len(variables) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.6 * ncols, 3.4 * nrows), squeeze=False)
    for ax in axes.ravel()[len(variables):]:
        ax.axis("off")
    for ax, v in zip(axes.ravel(), variables):
        perf = ctx.daily_perf(v)
        if perf.empty:
            _no_data(ax, v.name)
            continue
        draw_annual_cycle(ax, perf)
        ax.set_title(f"{v.name}\n{metrics_text(calculate_metrics(perf['OBS'], perf['SIM']), v.units)}",
                     fontsize=9)
        ax.set_ylabel(v.units)
    axes[0, 0].legend()
    fig.suptitle("Moyenne annuelle : cycle mensuel moyen (± écart-type interannuel)")
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/{name}")


# 02 : année d'exemple
def example_year(ctx, variables, year, out_dir):
    """Une année complète en moyennes journalières, panneaux empilés (axe x commun)."""
    variables = [v for v in variables if ctx.available(v)]
    fig, axes = plt.subplots(len(variables), 1, figsize=(12, 2.4 * len(variables)),
                             sharex=True, squeeze=False)
    for ax, v in zip(axes.ravel(), variables):
        perf = ctx.daily_perf(v)
        perf = perf[perf["Date"].dt.year == year]
        if perf.empty:
            _no_data(ax, f"{v.name} ({year})")
            continue
        style.plot_obs_sim(ax, perf["Date"], perf["OBS"], perf["SIM"], lw=1.0)
        ax.set_ylabel(f"{v.name}\n({v.units})", fontsize=8)
        ax.set_title(metrics_text(calculate_metrics(perf["OBS"], perf["SIM"]), v.units),
                     fontsize=8, loc="right")
    axes.ravel()[0].legend(loc="upper left", ncol=2)
    style.concise_dates(axes.ravel()[-1])
    fig.suptitle(f"Année d'exemple {year} (moyennes journalières)")
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/example_year_{year}.png")


#  03 / 05 : six graphiques
def six_panel(ctx, var, out_dir):
    """Figure de 6 panneaux pour UNE variable : moyenne annuelle + chaque période de cfg.periods.

    Résolution d'une période : pas de temps de CLASSIC si la période dure <= native_max_days
    jours (et si la sortie n'est pas journalière), sinon moyennes journalières.
    Retourne (chemin de la figure, liste de lignes de métriques).
    """
    cfg = ctx.cfg
    panels = [None] + list(cfg.periods)
    ncols = 3
    nrows = math.ceil(len(panels) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.3 * ncols, 4.0 * nrows), squeeze=False)
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")
    sim_daily_only = is_daily(ctx.classic[var.sim])
    rows = []

    for ax, p in zip(axes.ravel(), panels):
        if p is None:
            title, perf, res, t0, t1 = "Moyenne annuelle (cycle mensuel)", ctx.daily_perf(var), "mensuel", "", ""
            if not perf.empty:
                draw_annual_cycle(ax, perf)
        else:
            res = "journalier" if (sim_daily_only or p.n_days > cfg.native_max_days) else "natif"
            perf = align(ctx.obs, ctx.classic[var.sim], var.obs, var.sim, p.t0, p.t1,
                         resolution="daily" if res == "journalier" else "native")
            title, t0, t1 = f"{p.label}\n{p.start} → {p.end}", p.start, p.end
            if not perf.empty:
                style.plot_obs_sim(ax, perf["Date"], perf["OBS"], perf["SIM"],
                                   lw=1.0 if res == "natif" else 1.3)
                style.concise_dates(ax)
        if perf.empty:
            _no_data(ax, title)
            rows.append({"Variable": var.obs, "Panneau": title.split("\n")[0], "Début": t0,
                         "Fin": t1, "Résolution": res, "N": 0})
            continue
        m = calculate_metrics(perf["OBS"], perf["SIM"])
        ax.set_title(f"{title}\n{metrics_text(m, var.units)}", fontsize=9)
        ax.set_ylabel(var.units)
        rows.append({"Variable": var.obs, "Panneau": title.split("\n")[0], "Début": t0,
                     "Fin": t1, "Résolution": res, **m})

    axes[0, 0].legend(loc="best")
    fig.suptitle(f"Évaluation de {var.name} ({var.obs} vs {var.sim})", fontsize=13)
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/evaluation_{var.obs}.png"), rows


#  tableau de métriques
def metrics_all_years(ctx, variables):
    """Métriques journalières sur toutes les années communes + variabilité interannuelle."""
    rows = []
    for v in variables:
        if not ctx.available(v):
            continue
        perf = ctx.daily_perf(v)
        if perf.empty:
            continue
        rows.append({"Variable": v.obs, "Unités": v.units,
                     **calculate_metrics(perf["OBS"], perf["SIM"]), **iav(perf)})
    return pd.DataFrame(rows)


#  graphiques individuels (1 fichier / variable)
def annual_single(ctx, v, out_dir):
    """Cycle annuel moyen d'UNE variable, dans son propre fichier."""
    perf = ctx.daily_perf(v)
    if perf.empty:
        raise ValueError("aucune donnée commune")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    draw_annual_cycle(ax, perf)
    ax.set_title(f"{v.name} : moyenne annuelle\n{metrics_text(calculate_metrics(perf['OBS'], perf['SIM']), v.units)}",
                 fontsize=10)
    ax.set_ylabel(v.units)
    ax.legend()
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/annual_mean_{v.obs}.png")


def example_year_single(ctx, v, year, out_dir):
    """Année d'exemple (moyennes journalières) d'UNE variable, dans son propre fichier."""
    perf = ctx.daily_perf(v)
    perf = perf[perf["Date"].dt.year == year]
    if perf.empty:
        raise ValueError(f"aucune donnée commune en {year}")
    fig, ax = plt.subplots(figsize=(11, 4))
    style.plot_obs_sim(ax, perf["Date"], perf["OBS"], perf["SIM"], lw=1.2)
    ax.set_ylabel(f"{v.name} ({v.units})")
    ax.set_title(f"{v.name} : année {year}  |  {metrics_text(calculate_metrics(perf['OBS'], perf['SIM']), v.units)}",
                 fontsize=10)
    ax.legend(loc="upper left", ncol=2)
    style.concise_dates(ax)
    fig.tight_layout()
    return style.save(fig, f"{out_dir}/example_year_{year}_{v.obs}.png")
