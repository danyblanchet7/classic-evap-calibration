 #----charge pakage---------

print("...charging pakage")
import pandas as pd   
import netCDF4 as nc
import numpy as np

 #----charge fonction---------
print("...charging fonction")
from evaluation.metrics import calculate_metrics, print_metrics
print("1) fonction metrics ok ! ")
from evaluation.plot import plot_calibration
print("2) fonction plot ok ! ")
from evaluation.prepare import prepare_comparison
print("3) fonction prepare data shape ok ! ")
from evaluation.periods import select_month, select_year, growing_season, summer, select_period
print("4) fonction define periods ok ! ")

# CONFIG


OBS_PATH_FM = "C:/Users/danyblanchet7/Desktop/data analysis/data/"
CLASSIC_PATH_FM_K = r"\\wsl.localhost\Ubuntu\home\classic_ops\kyoungho_calibration\CA-MonJ\outputFiles\Juvenile_Transient\\"
OUTPUT_PATH = "/home/classic_ops/validation_kyoungho_results/"

YEAR = 2017
MONTH = 7
VARIABLES = [
    ("H_J", "hfss"),
    ("LE_J", "hfls"),

    # SW
    ("Rsd_J", "rsds"),
    ("Rsu_J", "rsus"),   # <-- calculer dans le module rsus-rlus.py

    # LW
    ("Rld_J", "rlds"),
    ("Rlu_J", "rlus"),   # <-- calculer dans le module rsus-rlus.py
]


PERIODS = [
    "month",
    "growing_season",
    "summer"
]

##----------------------------------------Load data------------------------

#Observation FM
print("...loading data obs")
dataE1 = pd.read_csv(OBS_PATH_FM + "EVAP 1.csv") #,index_col=0 )
print("EVAP 1 ok")
dataE2 = pd.read_csv(OBS_PATH_FM + "EVAP 2.csv") #,index_col=0 )
print("EVAP 2 ok")


obs_list = []  
obs_list.append(dataE1)
obs_list.append(dataE2)
obs = pd.concat(obs_list, ignore_index=True)




obs["Date"] = pd.to_datetime(
    obs[["Year", "Month", "Day", "Hour", "Minute"]]
)

obs = obs.sort_values("Date")  #trier par date 


#Simulation FM
print("... loading CLASSIC") 
################ debug
ds = nc.Dataset(CLASSIC_PATH_FM_K + "rss_halfhourly.nc")
print(ds.variables["rss"][:10])


classic_files = {
    "hfss": "hfss_halfhourly.nc",
    "hfls": "hfls_halfhourly.nc",

    # Rayonnement SW et LW
    "rsds": "rsds_halfhourly.nc",   # SW down
    "rss":  "rss_halfhourly.nc",    # SW net (SW absorbed)
    "rlds": "rlds_halfhourly.nc",   # LW down
    "rls":  "rls_halfhourly.nc",    # LW net (LW emitted)
}




classic = {}
for variable, filename in classic_files.items():

     print(f" loading {variable}") 

     dataset = nc.Dataset( CLASSIC_PATH_FM_K + filename ) 

     values = dataset.variables[variable][:, 0, 0] 

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
     classic[variable] = pd.DataFrame({ 
            "Date": pd.to_datetime(dates), 
            variable: values 
            }) 
     classic[variable] = classic[variable].sort_values( 
            "Date" 
            ) 
    
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
        obs_period = select_period(obs,period,YEAR, MONTH)
        sim_period = select_period( classic[sim_variable],period,YEAR, MONTH)
        perf = prepare_comparison( obs_period, sim_period, obs_variable, sim_variable )
        print("OBS :", len(obs_period))
        print("SIM :", len(sim_period))
        print("PERF :", len(perf))
        obs_values = perf["OBS"].values 
        sim_values = perf["SIM"].values 
        results = calculate_metrics( obs_values, sim_values )
        plot_calibration( perf, obs_variable, period)
        results_all.append({ "Variable": obs_variable, "Period": period, **results })
        print_metrics(results)


results_df = pd.DataFrame(results_all)



print("TABLEAU FINAL") 
print(" ") 
print(results_df)