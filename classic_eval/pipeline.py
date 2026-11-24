"""Orchestration : enchaîne les étapes dans l'ordre du protocole.

ÉTAPE        CONTENU                                                   DOSSIER
 annual      moyenne annuelle (cycle mensuel) de toutes les variables  01_moyenne_annuelle
 year        une année d'exemple (moyennes journalières)               02_annee_exemple
 fluxes      6 graphiques par variable : SW, LE, H, Rn                 03_flux_SW_LE_H
 heatmaps    RMSE / R² / biais par année x mois (LE, H, GPP, Rn, SW, LW) 03b_heatmaps
 snow        neige : hauteur obs/sim, variables, dates, albédo         04_neige
 others      6 graphiques des autres variables + diurne, phénologie,
             réponse aux forçages, eau du sol, racines                 05_autres
 surface     température de surface vs Rn (période + choisie)          06_Ts_vs_Rn
 budgets     bilan d'énergie (Rn cumulé) et bilan d'eau                07_bilans
 day         comportement de LE un jour donné vs forçages              08_jour_LE
 confidence  gabarit de confiance + disponibilité des obs              09_confiance

Chaque sous-étape est isolée : une erreur est affichée mais n'arrête pas les autres
(EVAL_DEBUG=1 dans l'environnement pour voir le détail).
"""
import os
import traceback
import pandas as pd

from . import (budgets, day_analysis, et_partition, evaluation, heatmaps, processes,
               snow, soil, style, surface, temporal)
from .context import Context
from .loaders import load_classic, load_obs
from .prepare import align

ALL_STAGES = ("annual", "year", "fluxes", "heatmaps", "snow", "others", "surface", "budgets", "day")


def _safe(name, fn):
    print(f"\n--- {name}")
    try:
        return fn()
    except Exception as e:                       # noqa: BLE001 : on isole volontairement
        print(f"  !! {name} ignoré : {type(e).__name__}: {e}")
        if os.environ.get("EVAL_DEBUG"):
            traceback.print_exc()
        return None


def _save(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"   tableau : {path}")


# étapes
def stage_annual(ctx):
    out = ctx.out("01_moyenne_annuelle")
    _safe("moyenne annuelle (cycle mensuel)", lambda: evaluation.annual_overview(ctx, ctx.cfg.variables, out))
    for v in ctx.cfg.variables:                      # + un fichier par variable
        if ctx.available(v):
            _safe(f"moyenne annuelle : {v.name}",
                  lambda v=v: evaluation.annual_single(ctx, v, os.path.join(out, "par_variable")))
    t = _safe("métriques journalières + IAV", lambda: evaluation.metrics_all_years(ctx, ctx.cfg.variables))
    if t is not None and len(t):
        _save(t, os.path.join(out, "metrics_daily_all_years.csv"))
        print(t.round(3).to_string())


def stage_year(ctx):
    out = ctx.out("02_annee_exemple")
    _safe(f"année d'exemple {ctx.cfg.example_year}",
          lambda: evaluation.example_year(ctx, ctx.cfg.variables, ctx.cfg.example_year, out))
    for v in ctx.cfg.variables:                      # + un fichier par variable
        if ctx.available(v):
            _safe(f"année {ctx.cfg.example_year} : {v.name}",
                  lambda v=v: evaluation.example_year_single(ctx, v, ctx.cfg.example_year,
                                                             os.path.join(out, "par_variable")))


def _six_panels(ctx, group, out):
    rows = []
    for v in ctx.cfg.variables:
        if (v.group == "flux") != (group == "flux"):
            continue
        if not ctx.available(v):
            print(f"  {v.obs}/{v.sim} indisponible, ignoré")
            continue
        r = _safe(f"6 graphiques : {v.name}", lambda v=v: evaluation.six_panel(ctx, v, out))
        if r:
            rows += r[1]
    if rows:
        _save(pd.DataFrame(rows), os.path.join(out, "metrics_by_period.csv"))


def stage_fluxes(ctx):
    _six_panels(ctx, "flux", ctx.out("03_flux_SW_LE_H"))


def stage_heatmaps(ctx):
    out, rows = ctx.out("03b_heatmaps"), []
    for v in ctx.cfg.variables:
        if v.obs in ctx.cfg.heatmap_vars and ctx.available(v):
            r = _safe(f"heatmap : {v.name}", lambda v=v: heatmaps.plot_heatmaps(ctx, v, out))
            if r:
                rows.append(r[1])
    if rows:
        _save(pd.concat(rows), os.path.join(out, "heatmap_metrics.csv"))


def stage_snow(ctx):
    cfg, out = ctx.cfg, ctx.out("04_neige")
    if "snd" in ctx.classic:
        _safe("variables de neige simulées",
              lambda: snow.plot_snow_variables(ctx.classic, cfg.snow_variables, out))
    if not cfg.obs_snow_csv:
        print("  cfg.obs_snow_csv non fourni : comparaisons avec les obs de neige ignorées")
    else:
        _safe("hauteur de neige obs vs CLASSIC",
              lambda: snow.plot_snow_depth_comparison(cfg.obs_snow_csv, ctx.classic, out,
                                                      cfg.snow_sites, cfg.snow_window))

        def seasons():
            obs_cm = temporal.load_obs_snow_daily(cfg.obs_snow_csv, cfg.snow_sites, *cfg.snow_window)
            sim_cm = ctx.classic["snd"].set_index("Date")["snd"].resample("1D").mean() * 100
            sim_cm = sim_cm[(sim_cm.index >= obs_cm.index.min()) & (sim_cm.index <= obs_cm.index.max())]
            t = temporal.compare_tables(temporal.snow_season_table(obs_cm, cfg.snow_threshold_cm),
                                        temporal.snow_season_table(sim_cm, cfg.snow_threshold_cm))
            t.to_csv(os.path.join(out, "snow_season_dates.csv"), encoding="utf-8-sig")
            print(t.to_string())
            if len(t):
                temporal.plot_event_comparison(t, "neige", out)
        _safe("début/fin de neige (années hydrologiques)", seasons)

        def check():
            t = temporal.verify_snow_dates(cfg.obs_snow_csv, ctx.classic, out, hy=cfg.snow_check_year,
                                           sites=cfg.snow_sites, thr_cm=cfg.snow_threshold_cm,
                                           melt_frac=cfg.melt_frac)
            print(t.to_string())
        _safe(f"vérification des dates de neige {cfg.snow_check_year}-{cfg.snow_check_year + 1}", check)

    def albedo():
        t, _ = processes.albedo_vs_snow(ctx.obs, ctx.classic, ctx.cfg.obs_cols, out)
        t.to_csv(os.path.join(out, "albedo_vs_snow.csv"), encoding="utf-8-sig")
        print(t.round(3).to_string())
    _safe("albédo vs état de la neige", albedo)
    if "albs" in ctx.classic and "snc" in ctx.classic:
        _safe("évolution de l'albédo", lambda: snow.plot_albedo_evolution(ctx.classic, out))


def stage_others(ctx):
    cfg, out = ctx.cfg, ctx.out("05_autres")
    _six_panels(ctx, "other", out)

    def diurnal():
        shifts = []
        for v in cfg.variables:
            if v.obs in cfg.diurnal_vars and ctx.available(v):
                perf = align(ctx.obs, ctx.classic[v.sim], v.obs, v.sim)
                if len(perf):
                    shifts.append(temporal.plot_diurnal(perf, v.name, v.units, out))
        t = pd.concat(shifts) if shifts else pd.DataFrame()
        _save(t, os.path.join(out, "diurnal_shifts.csv"))
        print(t.round(2).to_string())
    _safe("cycle diurne + déphasage", diurnal)

    def pheno():
        v = next(v for v in cfg.variables if v.sim == "gpp")
        d = ctx.daily_perf(v).set_index("Date")
        t = temporal.compare_tables(temporal.gpp_phenology_table(d["OBS"]),
                                    temporal.gpp_phenology_table(d["SIM"]))
        t.to_csv(os.path.join(out, "gpp_phenology.csv"), encoding="utf-8-sig")
        print(t.to_string())
        if len(t):
            temporal.plot_event_comparison(t, "GPP_phenologie", out)
    _safe("phénologie GPP", pheno)

    def responses():
        allr = []
        for fo, fs, flab in cfg.responses:
            for dname, (dcol, dlab) in cfg.drivers.items():
                try:
                    t = processes.binned_response(ctx.obs, ctx.classic, fo, fs, dcol, dlab, flab, out,
                                                  daytime_col=cfg.obs_cols["rsd"])
                    t.insert(0, "flux", flab)
                    t.insert(1, "driver_name", dname)
                    allr.append(t)
                except Exception as e:           # noqa: BLE001
                    print(f"  {flab} vs {dname} ignoré : {e}")
        if allr:
            _save(pd.concat(allr), os.path.join(out, "binned_responses.csv"))
    _safe("réponse aux forçages", responses)

    et_var = next((v for v in cfg.variables if v.sim == "et_mmd"), None)
    if et_var is not None and ctx.available(et_var):
        def et():
            path, clim = et_partition.plot_et_partition(ctx, et_var, cfg.example_year, out)
            _save(clim.reset_index(names="Mois"), os.path.join(out, "ET_partition_monthly.csv"))
            print(clim.round(3).to_string())
        _safe("partition de l'évapotranspiration (total / sol / végétation)", et)

    _safe("eau du sol par couche",
          lambda: soil.plot_soil_water_layers(cfg.classic_dir, out, cfg.soil_year))
    if "rootdpth" in ctx.classic:
        _safe("profondeur racinaire",
              lambda: soil.plot_root_depth(ctx.classic["rootdpth"], out, *cfg.root_years))


def stage_surface(ctx):
    _safe("Ts vs Rn", lambda: surface.plot_ts_vs_rn(ctx, ctx.out("06_Ts_vs_Rn")))


def stage_budgets(ctx):
    cfg, out = ctx.cfg, ctx.out("07_bilans")

    def energy(sub, g_obs, g_sim, label):
        """Un bilan d'énergie complet dans out/sub (g_obs / g_sim = None -> G ignoré)."""
        d = os.path.join(out, sub)
        os.makedirs(d, exist_ok=True)
        t, df, summ = budgets.energy_budget(ctx.obs, ctx.classic, cfg.obs_cols, g_obs=g_obs,
                                            g_sim=g_sim, g_sim_sign=cfg.g_sim_sign)
        t.to_csv(os.path.join(d, "energy_budget_monthly.csv"), encoding="utf-8-sig")
        budgets.plot_energy_closure(df, summ, d)
        periods = [("Toute la période", None), (f"Année {cfg.energy_year}", (cfg.energy_year,) * 2)]
        tot = budgets.plot_energy_cumulative(df, d, g_available=bool(summ["sim"].get("g_used")),
                                             weighted=cfg.energy_weighted, periods=periods,
                                             g_obs_available=bool(g_obs),
                                             suptitle=f"Rn cumulé et répartition de l'énergie ({label})")
        _save(tot, os.path.join(d, "energy_cumulative_totals.csv"))
        print(tot.round(1).to_string(index=False))
        print(pd.DataFrame(summ).round(3).to_string())
    _safe("bilan d'énergie 1 : sans G observé",
          lambda: energy("energie_sans_G_obs", None, cfg.g_sim, "sans G observé"))
    if cfg.g_obs and cfg.g_obs in ctx.obs.columns and cfg.g_sim:
        _safe(f"bilan d'énergie 2 : avec G ({cfg.g_obs} vs {cfg.g_sim})",
              lambda: energy("energie_avec_G", cfg.g_obs, cfg.g_sim, f"avec G : {cfg.g_obs} vs {cfg.g_sim}"))
    else:
        print("  2e bilan d'énergie ignoré : cfg.g_obs absent des observations ou cfg.g_sim = None")

    def water():
        if "mrso" not in ctx.classic:
            ctx.classic["mrso"] = budgets.load_total_soil_water(cfg.classic_dir)
        t, d = budgets.water_budget(ctx.classic)
        t.to_csv(os.path.join(out, "water_budget_monthly.csv"), encoding="utf-8-sig")
        budgets.plot_water_budget(d, out)
        if "snw" in ctx.classic:
            ty = budgets.plot_water_year(d, ctx.classic["snw"], out, years=cfg.water_years,
                                         obs_snow_csv=cfg.obs_snow_csv, snd=ctx.classic.get("snd"),
                                         sim_basis=cfg.snow_sim_basis, melt_frac=cfg.melt_frac,
                                         sites=cfg.snow_sites, thr_cm=cfg.snow_threshold_cm)
            _save(ty, os.path.join(out, "water_hydro_year_totals.csv"))
            print(ty.to_string())
    _safe("bilan d'eau", water)


def stage_day(ctx):
    if not ctx.cfg.day:
        print("  cfg.day non défini : étape ignorée")
        return
    out = ctx.out("08_jour_LE")
    r = _safe(f"LE le {ctx.cfg.day}", lambda: day_analysis.analyze_day(ctx, ctx.cfg.day, out))
    if r:
        print(r[1].round(2).to_string(index=False))




STAGE_FUNCS = {"annual": stage_annual, "year": stage_year, "fluxes": stage_fluxes,
               "heatmaps": stage_heatmaps, "snow": stage_snow,
               "others": stage_others, "surface": stage_surface, "budgets": stage_budgets,
               "day": stage_day}


def run(cfg, stages=ALL_STAGES):
    """Lance l'évaluation. `stages` : sous-ensemble de ALL_STAGES (dans cet ordre)."""
    style.setup()
    obs = load_obs(cfg)
    classic = load_classic(cfg)
    ctx = Context(cfg, obs, classic)
    for v in cfg.variables:                      # contrôle d'ordre de grandeur (unités)
        if v.obs in obs.columns and v.sim in classic:
            print(f"  médianes {v.name:<32} obs {obs[v.obs].median():>10.3g} | "
                  f"CLASSIC {classic[v.sim][v.sim].median():>10.3g}  {v.units}")
    for name in ALL_STAGES:
        if name in stages:
            print(f"\n{'=' * 70}\nÉTAPE : {name}\n{'=' * 70}")
            _safe(f"étape {name}", lambda f=STAGE_FUNCS[name]: f(ctx))
    print(f"\nTerminé. Résultats dans : {cfg.output_dir}")
    return ctx
