 ###Charge PAKAGE

print("...charging pakage")
import pandas as pd   
import netCDF4 as nc
import numpy as np

 ###Charge FONCTIONS

print("...charging fonction")
from evaluation.metrics import calculate_metrics, print_metrics
print("-1 fonction metrics ok ! ")
from evaluation.plot import plot_calibration
print("-2 fonction plot ok ! ")
from evaluation.prepare import prepare_comparison
print("-3 fonction prepare data shape ok ! ")
from evaluation.periods import select_month, select_year, growing_season, summer, select_period
print("-4 fonction define periods ok ! ")
from evaluation.Dailyplot import ( plot_daily_timeseries, plot_monthly_timeseries)

# CONFIG


OBS_PATH_FM = "C:/Users/danyblanchet7/Desktop/data analysis/data/"
CLASSIC_PATH_FM_K = r"\\wsl.localhost\Ubuntu\home\danyblanchet7\CLASSIC\outputFiles\Juvenile_Transient\\"
OUTPUT_PATH = "C:/Users/danyblanchet7/Desktop/data analysis/FM/"

YEAR = 2021
MONTH = 7
START_DAY = 10
END_DAY = 20

SOIL_LAYER_INDEX = 0    


# VARIABLE (COUPLE = variable_obs, variable_sim) comparés avec métriques + graphique

VARIABLES = [
    ("H_J", "hfss"),
    ("LE_J", "hfls"),
 
 
    # SW
    ("Rsd_J", "rsds"),
    ("Rsu_J", "rsus"),   # calculé à partir de rsds - rss
 
    # LW
    ("Rld_J", "rlds"),
    ("Rlu_J", "rlus"),   # calculé à partir de rlds - rls
 
    # Eau dans le sol
    ("VWC_J", "mrsol"),
 
    # Température du sol
    ("Tsoil_J", "tsl"),
 
    # GPP : deux méthodes de partitionnement obs (DT/NT),
    ("GPP_DT_J_gf2", "gpp"),
   # ("GPP_NT_J_gf2", "gpp"),
]

    #SNOW

SNOW_VARIABLES = {
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
obs["Date"] = pd.to_datetime(
    obs[["Year", "Month", "Day", "Hour", "Minute"]]
)

obs = obs.sort_values("Date")  #trier par date 
print("Done!")

##LOAD DAT SIM

# FM

print("... loading CLASSIC") 

classic_files = {
    # LE et H
    "hfss": "hfss_halfhourly.nc",
    "hfls": "hfls_halfhourly.nc",

    # Rayonnement SW et LW
    "rsds": "rsds_halfhourly.nc",   # SW down
    "rss":  "rss_halfhourly.nc",    # SW net (SW absorbed)
    "rlds": "rlds_halfhourly.nc",   # LW down
    "rls":  "rls_halfhourly.nc",    # LW net (LW emitted)

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

classic = {}

for variable, filename in classic_files.items():

     print(f" loading {variable}") 

     dataset = nc.Dataset( CLASSIC_PATH_FM_K + filename ) 

     ### sans couche de sol ## values = dataset.variables[variable][:, 0, 0] 
     
     raw = dataset.variables[variable]


    # Les variables de sol (mrsol, tsl) ont une dimension de couche en plus
    # (time, layer, lat, lon) au lieu de (time, lat, lon)
     if raw.ndim == 4:
        values = raw[:, SOIL_LAYER_INDEX, 0, 0]
     else:
        values = raw[:, 0, 0]

     time = dataset.variables["time"] 

     dates = nc.num2date( 
        time[:], 
        units=time.units, 
        calendar=getattr( 
            time, 
            "calendar", 
            "standard" 
            ), 
            only_use_cftime_datetimes=False 
        ) 
     df = pd.DataFrame({"Date": pd.to_datetime(dates), variable: values})
     df = df.sort_values("Date")
 
    # Conversion d'unités GPP : kgC/m2/s -> gC/m2/jour
     if variable == "gpp":
        df["gpp"] = df["gpp"] * 86400 * 1000
 
     classic[variable] = df
     dataset.close()
     print(f" {variable} ok")
 
print("... computing rsus and rlus")

# SW↑ = SW↓ − SW_net
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

# CALCUL DES PERFORMANCES 

results_all = [] 

for obs_variable, sim_variable in VARIABLES: 
    print(f"VARIABLE : {obs_variable} vs {sim_variable}") 
    
    for period in PERIODS:
        print(f"\n--- {period} ---")
        obs_period = select_period(obs,period,YEAR, MONTH, START_DAY, END_DAY)
        sim_period = select_period( classic[sim_variable],period,YEAR, MONTH, START_DAY, END_DAY)
        perf = prepare_comparison( obs_period, sim_period, obs_variable, sim_variable )
        print("OBS :", len(obs_period)) 
        print("SIM :", len(sim_period))
        print("PERF :", len(perf))
        obs_values = perf["OBS"].values 
        sim_values = perf["SIM"].values 
        results = calculate_metrics( obs_values, sim_values )
        plot_calibration( perf, obs_variable, period)
        results_all.append({ "Variable": obs_variable, "Period": period, **results })
        #print_metrics(results)


results_df = pd.DataFrame(results_all)



print("TABLEAU FINAL") 
print(" ") 
print(results_df)

########################################################AMELIORER A PARTIR D'ICI

# ----------------------------------------------------------
# SERIES TEMPORELLES HORAIRES SUR TOUTE LA PERIODE
# ----------------------------------------------------------

print("... plotting hourly time series")

plot_daily_timeseries(
    obs,
    classic["hfss"],
    "H_J",
    "hfss",
    OUTPUT_PATH + "H_daily_all_years.png",
    title="H Évolution horaire sur toute la période"
)

plot_daily_timeseries(
    obs,
    classic["hfls"],
    "LE_J",
    "hfls",
    OUTPUT_PATH + "LE_daily_all_years.png",
    title="LE Évolution horaire sur toute la période"
)

print("Daily time series saved.")


# ----------------------------------------------------------
# SERIES TEMPORELLES MENSUELLES - TOUTE LA PERIODE
# ----------------------------------------------------------

print("... plotting monthly time series")

plot_monthly_timeseries(
    obs,
    classic["hfss"],
    "H_J",
    "hfss",
    OUTPUT_PATH + "H_monthly_all_years.png",
    title="H Évolution mensuelle sur toute la période"
)

plot_monthly_timeseries(
    obs,
    classic["hfls"],
    "LE_J",
    "hfls",
    OUTPUT_PATH + "LE_monthly_all_years.png",
    title="LE Évolution mensuelle sur toute la période"
)

print("Monthly time series saved.")


import matplotlib.pyplot as plt
# ----------------------------------------------------------
# NEIGE - séries simulées sur toute la période
# ----------------------------------------------------------

print("... plotting snow variables")

fig, axes = plt.subplots(
    4, 1,
    figsize=(12, 12),
    sharex=True
)

for ax, (var, label) in zip(axes, SNOW_VARIABLES.items()):

    df_snow = classic[var]

    ax.plot(
        df_snow["Date"],
        df_snow[var],
        linewidth=1
    )

    ax.set_ylabel(label)
    ax.set_title(f"CLASSIC - {var}")

    ax.grid(True, alpha=0.3)

axes[-1].set_xlabel("Date")

plt.tight_layout()

plt.savefig(
    OUTPUT_PATH + "snow_variables_simulated_all_years.png",
    dpi=150
)

plt.close()

print("Snow plot saved.")



#-------------- root depth pas encore calculé dans classic
ROOT_YEAR = 2021

root_df = classic["rootdpth"]
root_2022 = root_df[root_df["Date"].dt.year == ROOT_YEAR]
root_gs_2022 = root_2022[
    (root_2022["Date"].dt.month >= 5) &
    (root_2022["Date"].dt.month <= 9)
]

print("... plotting root depth annual 2022")

root_df = classic["rootdpth"]
root_2022 = root_df[root_df["Date"].dt.year == 2022]

plt.figure(figsize=(10,5))
plt.plot(root_2022["Date"], root_2022["rootdpth"], marker="o", linewidth=2)
plt.ylabel("Profondeur racinaire (m)")
plt.title("CLASSIC – Profondeur racinaire (Annuel 2022)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_PATH + "root_depth_annual_2022.png", dpi=150)
plt.close()


print("... plotting root depth growing season 2022")

root_gs_2022 = root_2022[
    (root_2022["Date"].dt.month >= 5) &
    (root_2022["Date"].dt.month <= 9)
]

plt.figure(figsize=(10,5))
plt.plot(root_gs_2022["Date"], root_gs_2022["rootdpth"], marker="o", linewidth=2)
plt.ylabel("Profondeur racinaire (m)")
plt.title("CLASSIC – Profondeur racinaire (Growing Season 2022)")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_PATH + "root_depth_growing_season_2022.png", dpi=150)
plt.close()


# ----------------------------------------------------------eau sol
import os


# dossier de sortie Windows
OUTPUT_SOIL = r"C:\Users\danyblanchet7\Desktop\Data analysis\my-python-project\result\eau_sol"
os.makedirs(OUTPUT_SOIL, exist_ok=True)

# --- Recharger mrsol_daily.nc proprement ---
mrsol_path = CLASSIC_PATH_FM_K + "mrsol_daily.nc"
ds_mrsol = nc.Dataset(mrsol_path)

raw = ds_mrsol.variables["mrsol"]      # (time, layer, lat, lon)
time = ds_mrsol.variables["time"]

dates = nc.num2date(
    time[:],
    units=time.units,
    calendar=getattr(time, "calendar", "standard")
)

# convertir en DataFrame
# convertir en DataFrame (conversion cftime -> datetime64)
df = pd.DataFrame({"Date": [pd.Timestamp(d.isoformat()) for d in dates]})


# nombre de couches
n_layers = raw.shape[1]

YEAR_SOIL = 2021

# tracer chaque couche
for layer in range(n_layers):

    # extraire la couche
    df_layer = df.copy()
    df_layer["mrsol"] = raw[:, layer, 0, 0]

    # filtrer l'année
    df_annual = df_layer[df_layer["Date"].dt.year == YEAR_SOIL]

    # tracer
    plt.figure(figsize=(10,5))
    plt.plot(df_annual["Date"], df_annual["mrsol"], linewidth=1.5)
    plt.ylabel("mrsol (kg/m²)")
    plt.title(f"CLASSIC – Eau du sol – Couche {layer} – Annuel {YEAR_SOIL}")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # enregistrer
    outpath = os.path.join(OUTPUT_SOIL, f"mrsol_layer{layer}_annual_{YEAR_SOIL}.png")
    plt.savefig(outpath, dpi=150)
    plt.close()

ds_mrsol.close()


