# CONVENTION GRAPHIQUE : observations = gris foncé, CLASSIC = bleu (voir classic_eval/style.py).
#ici Chaque sous-étape est isolée (_safe). 
# Si le bilan d’eau plante parce qu’une variable manque, le reste continue et l’erreur est affichée. 
# EVAL_DEBUG=1 affiche le détail technique.
from classic_eval import EvalConfig, Period, Variable, run

###Directory
cfg = EvalConfig(
    obs_dir=r"C:/Users/danyblanchet7/Desktop/data analysis/data/",
    classic_dir=r"\\wsl.localhost\Ubuntu\home\danyblanchet7\CLASSIC\outputFiles\Juvenile_Transient",
    output_dir=r"C:/Users/danyblanchet7/Desktop/data analysis/FM/Evaluation",
    obs_files=["EVAP 1.csv", "EVAP 2.csv"],
    obs_snow_csv=r"C:/Users/danyblanchet7/Desktop/data analysis/data/snow_database_FM_23_25(in).csv",

    # Choix de 5 périodes pour l'évaluation par variable.
    periods=[
        Period("Hiver",       "2021-01-10", "2021-01-25"),
        Period("Fonte",       "2021-04-15", "2021-05-15"),
        Period("Début d'été", "2021-06-10", "2021-06-25"),
        Period("Plein été",   "2021-07-15", "2021-07-31"),
        Period("Automne",     "2021-10-01", "2021-10-15"),
    ],

    #SETTING
    example_year=2021,                                           # étape 02
    surface_period=Period("Ts vs Rn", "2021-06-10", "2021-06-25"),  # étape 06
    day="2021-06-15",                                            # étape 08 : jour analysé pour LE
    energy_year=2021,                                            # étape 07 : année du cumul de Rn
    soil_year=2022, root_years=(2016, 2024),
    snow_check_year=2023, water_years=(2023,),

    # CONVERSIONS D'UNITÉS 
    gpp_factor=1e9 / 12.011,        # kg C m-2 s-1 -> µmol CO2 m-2 s-1 
    soil_layer=0, soil_layer_thickness=0.1,
    npp_sign=-1,                    # NEE ~ -NPP (CLASSIC) 
    et_obs_col="ET_J_ful", et_obs_factor=48.0,   # ET_J_ful supposée en mm/30 min -> mm/j
    g_obs="G_J_ful",                # 2e bilan d'énergie (avec G observé)
    g_sim="gflx", g_sim_sign=1,     # passer à -1 si G est négatif en plein jour d'été

    #Pour ajouter une AUTRE variable : cfg.variables = [Variable("col_obs", "var_classic", "unités", "Nom", "flux"), ...]
)

if __name__ == "__main__":
    run(cfg)          
