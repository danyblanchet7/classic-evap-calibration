 ###Charge PAKAGE

print("...charging pakage")
import pandas as pd   
import netCDF4 as nc
import numpy as np

 ### Charge FONCTIONS

print("...charging fonction from modules")
from evaluation.metrics import calculate_metrics, print_metrics
print("-1 fonction metrics ok ! ")
from evaluation.plot import plot_calibration
print("-2 fonction plot ok ! ")
from evaluation.prepare import prepare_comparison
print("-3 fonction prepare data shape ok ! ")
from evaluation.periods import select_month, select_year, growing_season, summer, select_period
print("-4 fonction periods ok ! ")
from evaluation.monthly_analysis import analyze_monthly_outputs
print("-5 fonction monthly series ok ! ")
from evaluation.snow_analysis import plot_snow_variables
print("-6 fonction snow analysis ok ! ")
from evaluation.mrsol import plot_soil_water_layers
print("-7 fonction water in soil analysis ok ! ")
from evaluation.Roots import (plot_root_depth)
print("-8 fonction roots analysis ok ! ")
# CONFIG


OBS_PATH_FM = "C:/Users/danyblanchet7/Desktop/data analysis/data/"
CLASSIC_PATH_FM_K = r"\\wsl.localhost\Ubuntu\home\danyblanchet7\CLASSIC\outputFiles\Juvenile_Transient\\"
OUTPUT_PATH = "C:/Users/danyblanchet7/Desktop/data analysis/FM/FM/"
OUTPUT_MONTHLY = "C:/Users/danyblanchet7/Desktop/data analysis/FM/Monthly/"
OUTPUT_WSOIL = "C:/Users/danyblanchet7/Desktop/data analysis/FM/SWC/"
OUTPUT_SNOW = "C:/Users/danyblanchet7/Desktop/data analysis/FM/SNOW/"

YEAR = 2021
MONTH = 7
START_DAY = 10
END_DAY = 25

#couche de sol que je veux analyser 
SOIL_LAYER_INDEX = 0 
YEAR_SOIL = 2022

ROOT_YEAR = 2021


# VARIABLE (COUPLE = variable_obs, variable_sim) comparés avec métriques + graphique

VARIABLES = np.array([
    ("H_J", "hfss", "W.m-2"),
    ("LE_J", "hfls", "W.m-2"),
 
    # SW
    ("Rsd_J", "rsds", "W.m^2"),
    ("Rsu_J", "rsus", "W.m^2"),   # calculé à partir de rsds - rss
 
    # LW
    ("Rld_J", "rlds", "W.m^2"),
    ("Rlu_J", "rlus", "W.m^2"),   # calculé à partir de rlds - rls
 
    # Eau dans le sol
    ("VWC_CS651_J", "mrsol", "frac"),
 
    # Température du sol
    ("Tsoil_J", "tsl", "K"),
 
    # GPP : deux méthodes de partitionnement obs (DT/NT),
    ("GPP_DT_J_gf2", "gpp", "umol s-1 m-2"),
   # ("GPP_NT_J_gf2", "gpp"),
])

    #SNOW

SNOW_VARIABLES = {   #dictionnaire 
    "snw": "SWE (kg/m2)",
    "snc": "Couverture (%)",
    "snm": "Fonte (kg/m2/s)",
    "snd": "Profondeur (m)",
}


PERIODS = [
   # "annual",
    "month",
   # "growing_season",
    "summer",
    "days"
]

##LOAD DAT OBS

#FM

print("...loading data obs")
dataE1 = pd.read_csv(OBS_PATH_FM + "EVAP 1.csv") #,index_col=0 )
print("EVAP 1 ok")
dataE2 = pd.read_csv(OBS_PATH_FM + "EVAP 2.csv") #,index_col=0 )
print("EVAP 2 ok")


obs_list = []  
obs_list.append(dataE1)
obs_list.append(dataE2)
obs = pd.concat(obs_list, ignore_index=True)

#conversion en datetime
obs["Date"] = pd.to_datetime(obs[["Year", "Month", "Day", "Hour", "Minute"]])

obs = obs.sort_values("Date")  #trier par date 
print("Done!")

##LOAD DAT SIM

# FM

print("... loading CLASSIC") 
 
classic_files = {                 ###Dictionnaire
    # LE et H
    "hfss": "hfss_halfhourly.nc",
    "hfls": "hfls_halfhourly.nc",
    

    # Rayonnement SW et LW
    "rsds": "rsds_halfhourly.nc",   # SW down
    "rss":  "rss_halfhourly.nc",    # SW net (SW absorbed)
    "rlds": "rlds_halfhourly.nc",   # LW down
    "rls":  "rls_halfhourly.nc",    # LW net (fif between emitted and arrived)

    # Snow
    "snw" : "snw_daily.nc", #SWE
    "snc" : "snc_daily.nc", #couverture %
    "snm" : "snm_daily.nc",   #fonte
    "snd" : "snd_daily.nc", #couverture
    
    # Eau et température du sol (seulement journalier dispo)
 
    "mrsol": "mrsol_daily.nc",
    "tsl":   "tsl_daily.nc",
 
    # GPP
    "gpp": "gpp_halfhourly.nc",

    #root depth
    "rootdpth": "rootdpth_monthly_perpft.nc",
 }

classic = {}                      ###Gestion des output CLASSIC

classic = {}

for variable, filename in classic_files.items():

    print(f" loading {variable}")

    dataset = nc.Dataset(CLASSIC_PATH_FM_K + filename)
    Vraw = dataset.variables[variable]

    # =========================================================
    # ROOT DEPTH : on conserve les PFT
    # =========================================================
    if variable == "rootdpth":

        # Dimensions de la variable
        print("   rootdpth dimensions :", Vraw.dimensions)
        print("   rootdpth shape :", Vraw.shape)

        # On récupère PFT 1 et PFT 8
        values_pft1 = Vraw[:, 0, 0, 0]
        values_pft8 = Vraw[:, 7, 0, 0]

        time = dataset.variables["time"]

        dates = nc.num2date(
            time[:],
            units=time.units,
            only_use_cftime_datetimes=False
        )

        root_df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "PFT1": values_pft1,
            "PFT8": values_pft8
        })

        root_df = root_df.sort_values("Date")

        classic[variable] = root_df
        root = dataset.variables["rootdpth"]

        print(root.dimensions)
        print(root.shape)

        print(root[:, 0, 0, 0])
        print(root[:, 7, 0, 0])
        dataset.close()

        print(" rootdpth PFT1/PFT8 ok")


    # AUTRES VARIABLES 

    else:

        if Vraw.ndim == 4:
            values = Vraw[:, SOIL_LAYER_INDEX, 0, 0]
        else:
            values = Vraw[:, 0, 0]

        time = dataset.variables["time"]

        dates = nc.num2date(
            time[:],
            units=time.units,
            only_use_cftime_datetimes=False
        )

        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            variable: values
        })

        df = df.sort_values("Date")

        # Conversion GPP
        if variable == "gpp":
            df["gpp"] = df["gpp"] * 86400 * 1000

        # Conversion mrsol
        if variable == "mrsol":
            rho_eau = 1000.0
            delz = 0.1
            df["mrsol"] = df["mrsol"] / (rho_eau * delz)

        classic[variable] = df

        dataset.close()

        print(f" {variable} ok")
 
print("... computing rsus and rlus")

# ajout au dictionnaire classic de SW↑ = SW↓ − SW_net
classic["rsus"] = pd.DataFrame({
    "Date": classic["rsds"]["Date"],
    "rsus": classic["rsds"]["rsds"].values - classic["rss"]["rss"].values
})

# LW↑ = LW↓ − LW_net
classic["rlus"] = pd.DataFrame({
    "Date": classic["rlds"]["Date"],
    "rlus": classic["rlds"]["rlds"].values - classic["rls"]["rls"].values
})

print("rsus / rlus OK")




# CALCUL DES PERFORMANCES ET GRAPH

results_all = [] 

for obs_variable, sim_variable, units, in VARIABLES: 
    #print(f"VARIABLE : {obs_variable} vs {sim_variable}") 
    
    for period in PERIODS:      
        #print(f"\n--- {period} ---")
        obs_period = select_period(obs,period,YEAR, MONTH, START_DAY, END_DAY)
        sim_period = select_period( classic[sim_variable],period,YEAR, MONTH, START_DAY, END_DAY)
        perf = prepare_comparison( obs_period, sim_period, obs_variable, sim_variable ) ##merge les obs et simulations
        #print("OBS :", len(obs_period)) 
        #print("SIM :", len(sim_period))
        #print("PERF :", len(perf))
        if perf.empty or perf["OBS"].dropna().empty:
            print(f"  {obs_variable} vs {sim_variable} | {period} : aucune observation disponible — ignoré.")
            results_all.append({
                "Variable": obs_variable,
                "Period": period,
                "Note": "Obs manquantes"
            })
            continue  # passe à l'itération suivante, ne plante pas
        obs_values = perf["OBS"].values 
        sim_values = perf["SIM"].values 
        results = calculate_metrics( obs_values, sim_values )
        plot_calibration(perf, obs_variable, period, units, OUTPUT_PATH)
        results_all.append({ "Variable": obs_variable, "Period": period, **results }) 
        #print_metrics(results)


results_df = pd.DataFrame(results_all)



print("TABLEAU FINAL PERFORMANCES :") 
print(" ") 
print(results_df)


########################################################



print("... plotting monthly time series")
analyze_monthly_outputs(
    obs=obs,
    classic_path=CLASSIC_PATH_FM_K,
    output_path=OUTPUT_MONTHLY
)

print("Monthly time series saved.")

plot_snow_variables(
    classic=classic,
    snow_variables=SNOW_VARIABLES,
    output_path=OUTPUT_SNOW + "snow_variables_simulated_all_years.png"
)

plot_soil_water_layers(
    CLASSIC_PATH_FM_K,
    OUTPUT_WSOIL,
    YEAR_SOIL
)
root_df=classic["rootdpth"]
output_path=OUTPUT_PATH



plot_root_depth(
    root_df,
    OUTPUT_PATH,
    2016,
    2024
)
