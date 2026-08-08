 #----charge pakage---------
 
import pandas as pd   
import matplotlib.pyplot as plt   
import netCDF4 as nc
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np



# ============================================================
# CONFIG
#----------------------------------------define path ---------

OBS_PATH_FM = "C:/Users/danyblanchet7/Desktop/data analysis/my-python-project/data/"
CLASSIC_PATH_FM_K = r"\\wsl.localhost\Ubuntu\home\classic_ops\kyoungho_calibration\CA-MonJ\outputFiles\Juvenile_Transient\\"
OUTPUT_PATH = "/home/classic_ops/validation_kyoungho_results/"

##----------------------------------------Data------------------------

#Observation FM

dataE1 = pd.read_csv(OBS_PATH_FM + "EVAP 1.csv") #,index_col=0 )
dataE2 = pd.read_csv(OBS_PATH_FM + "EVAP 2.csv") #,index_col=0 )

#Simulation FM

dataSK = nc.Dataset(CLASSIC_PATH_FM_K + "hfss_halfhourly.nc")

#----------------------------------------define periode ---------------

VARIABLE_OBS = "H_J"
VARIABLE_SIM = "hfss"
YEAR = 2018
MONTH = 7
DAY = 12

#----------------------------------------lire data obs ----------------

print("-" * 30)
print("CLASSIC VS OBSERVATIONS - " + str(YEAR) + "/" + str(MONTH) + "/" + str(DAY))
print("-" * 30)

obs_list = []  
obs_list.append(dataE1)
obs_list.append(dataE2)
obs = pd.concat(obs_list, ignore_index=True)


obs["Date"] = pd.to_datetime(
    obs[["Year", "Month", "Day", "Hour", "Minute"]]
)

obs = obs.sort_values("Date")  #trier par date 
obs_juillet = obs[
    (obs["Date"].dt.year == YEAR) &
    (obs["Date"].dt.month == MONTH) #&
    #(obs["Date"].dt.day == DAY)
]

#### plot

plt.figure(figsize=(12,4))
plt.plot(
    obs_juillet["Date"],
    obs_juillet[VARIABLE_OBS],
    label="Observations",
    color="red"
)


plt.xlabel("Date")
plt.ylabel(VARIABLE_OBS + "(  W m$^{-2}$)")
plt.title(VARIABLE_OBS + " - " + str(YEAR) + "/" + str(MONTH) + "/" + str(DAY))
plt.legend()
plt.show()


###lire data sim


# Variable
sim = dataSK.variables[VARIABLE_SIM][:, 0, 0]      # (temps, lat, lon)

# Temps
time = dataSK.variables["time"]
dates = nc.num2date(
    time[:],
    units=time.units,
    calendar=getattr(time, "calendar", "standard"),
    only_use_cftime_datetimes=False
)

# DataFrame
classic = pd.DataFrame({
    "Date": pd.to_datetime(dates),
    "H": sim
})

# Tri
classic = classic.sort_values("Date")

# Filtre
sim_juillet = classic[
    (classic["Date"].dt.year == YEAR) &
    (classic["Date"].dt.month == MONTH) #&
  #  (classic["Date"].dt.day == DAY)
]

##plot


plt.figure(figsize=(12,4))
plt.plot(
    sim_juillet["Date"],
    sim_juillet["H"],
    label="Simulation",
    color="blue"
)

plt.xlabel("Date")
plt.ylabel(VARIABLE_SIM + "(  W m$^{-2}$)")
plt.title(VARIABLE_SIM + " - " + str(YEAR) + "/" + str(MONTH) + "/" + str(DAY))
plt.legend()
plt.show()


print(classic.head())
print(classic.tail())

print("Période CLASSIC :")
print(classic["Date"].min(), classic["Date"].max())

print("Nombre de points après filtre :")
print(len(sim_juillet))

print(sim_juillet)

###plot 2

plt.figure(figsize=(12,4))
plt.plot(
    obs_juillet["Date"],
    obs_juillet[VARIABLE_OBS],
    color="blue",
    linewidth=0.7,
    label="Observations"
)

plt.plot(
    sim_juillet["Date"],
    sim_juillet["H"],
    color="red",
    linewidth=0.7,
    label="CLASSIC"
)



plt.xlabel("Date")
plt.ylabel(VARIABLE_SIM + "(  W m$^{-2}$)")
plt.title(VARIABLE_SIM + " - " + str(YEAR) + "/" + str(MONTH) + "/" + str(DAY))
plt.legend()
plt.show()


# Métrique de performance 

# Fusion sur les dates communes
perf = pd.merge(
    obs_juillet[["Date", VARIABLE_OBS]],
    sim_juillet[["Date", "H"]],
    on="Date",
    how="inner"
)

perf = perf.dropna()



# CALCUL DES METRIQUES
# ------------------------------------------------------------
####
obs_values = perf[VARIABLE_OBS].values
sim_values = perf["H"].values


# RMSE
rmse = np.sqrt(
    mean_squared_error(obs_values, sim_values)
)

# MAE
mae = mean_absolute_error(
    obs_values,
    sim_values
)

# Bias moyen
bias = np.mean(
    sim_values - obs_values
)

# Corrélation
r = np.corrcoef(
    obs_values,
    sim_values
)[0,1]


# R2
r2 = r2_score(
    obs_values,
    sim_values
)


# Nash-Sutcliffe Efficiency
nse = 1 - (
    np.sum((obs_values - sim_values)**2) /
    np.sum((obs_values - np.mean(obs_values))**2)
)

# AFFICHAGE
# ------------------------------------------------------------

print("\n------------------")
print(" PERFORMANCE CLASSIC VS OBS ") 
print("--------------------")

print(f"RMSE  : {rmse:.2f} W m-2")
print(f"MAE   : {mae:.2f} W m-2")
print(f"Bias  : {bias:.2f} W m-2")
print(f"r     : {r:.3f}")
print(f"R2    : {r2:.3f}")
print(f"NSE   : {nse:.3f}")