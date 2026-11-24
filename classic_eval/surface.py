"""Température de surface vs rayonnement net (étape 06).

Deux figures : toute la période (moyennes journalières) et la période choisie
(cfg.surface_period ; pas de temps natif si <= native_max_days). À droite : relation Ts = f(Rn).
"""
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from . import style
from .prepare import align


def _ts_rn(ctx, t0=None, t1=None, resolution="daily"):
    ts_var = next((v for v in ctx.cfg.variables if v.sim == "ts"), None)
    if ts_var is None or "rn" not in ctx.classic or "Rn_obs" not in ctx.obs.columns:
        raise KeyError("il faut une variable (obs, 'ts') dans cfg.variables et Rn obs/sim disponibles")
    ts = align(ctx.obs, ctx.classic["ts"], ts_var.obs, "ts", t0, t1, resolution)
    rn = align(ctx.obs, ctx.classic["rn"], "Rn_obs", "rn", t0, t1, resolution)
    return ts, rn, ts_var


def _figure(ts, rn, ts_var, title, path):
    fig = plt.figure(figsize=(15, 6.5))
    gs = GridSpec(2, 3, figure=fig)
    ax1 = fig.add_subplot(gs[0, :2])
    ax2 = fig.add_subplot(gs[1, :2], sharex=ax1)
    ax3 = fig.add_subplot(gs[:, 2])
    style.plot_obs_sim(ax1, ts["Date"], ts["OBS"], ts["SIM"], lw=1.0)
    style.plot_obs_sim(ax2, rn["Date"], rn["OBS"], rn["SIM"], lw=1.0)
    ax1.set_ylabel(f"{ts_var.name} ({ts_var.units})")
    ax2.set_ylabel("Rn (W m-2)")
    ax1.legend(loc="upper left", ncol=2)
    style.concise_dates(ax2)
    both = ts.merge(rn, on="Date", suffixes=("_ts", "_rn"))
    ax3.scatter(both["OBS_rn"], both["OBS_ts"], s=8, alpha=0.5, color=style.OBS_COLOR, label=style.OBS_LABEL)
    ax3.scatter(both["SIM_rn"], both["SIM_ts"], s=8, alpha=0.5, color=style.SIM_COLOR, label=style.SIM_LABEL)
    ax3.set_xlabel("Rn (W m-2)")
    ax3.set_ylabel(f"{ts_var.name} ({ts_var.units})")
    ax3.set_title("Ts en fonction de Rn")
    ax3.legend()
    fig.suptitle(title, fontsize=13)
    fig.tight_layout()
    return style.save(fig, path)


def plot_ts_vs_rn(ctx, out_dir):
    """Figure toute période + figure sur la période choisie. Retourne la liste des fichiers."""
    files = []
    ts, rn, v = _ts_rn(ctx)
    if len(ts) and len(rn):
        files.append(_figure(ts, rn, v, "Température de surface vs Rn : toute la période (moyennes journalières)",
                             f"{out_dir}/Ts_vs_Rn_all_period.png"))
    p = ctx.cfg.surface_period
    if p is None:
        print("  cfg.surface_period non défini : figure de période ignorée")
        return files
    res = "daily" if p.n_days > ctx.cfg.native_max_days else "native"
    ts, rn, v = _ts_rn(ctx, p.t0, p.t1, res)
    if ts.empty or rn.empty:
        print(f"  aucune donnée Ts/Rn commune pour {p.label}")
        return files
    files.append(_figure(ts, rn, v, f"Température de surface vs Rn : {p.label} ({p.start} → {p.end})",
                         f"{out_dir}/Ts_vs_Rn_{p.start}_{p.end}.png"))
    return files
