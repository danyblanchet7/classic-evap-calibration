import pandas as pd
import netCDF4 as nc
import numpy as np
import matplotlib.pyplot as plt
import os

#    
# ============================================================
# 1. Charger les observations (EVAP1 + EVAP2 MAJ 22/06/2026)
# ============================================================

#EVAP1
obs1 = pd.read_csv(r"C:/Users/danyblanchet7/Desktop/EVAP 1.csv")

#EVAP2
obs2 = pd.read_csv(r"C:/Users/danyblanchet7/Desktop/EVAP 2.csv")

# Fusion des deux jeux de données
obs = pd.concat([obs1, obs2], ignore_index=True)

# Création de la date
obs["Date"] = pd.to_datetime(dict(
    year=obs["Year"],
    month=obs["Month"],
    day=obs["Day"],
    hour=obs["Hour"],
    minute=obs["Minute"]
))

# Tri chronologique
obs = obs.sort_values("Date")

# Suppression d'éventuels doublons
obs = obs.drop_duplicates(subset="Date")

# Date en index
obs = obs.set_index("Date")

#--------
print("Période observations : " + str(obs.index.min()) + " to " + str(obs.index.max()))



# ============================================================
# Choisir la variable observée
# ============================================================

# L'évapotranspiration :
obs_daily = (
    obs["ET_J"]
    .resample("D")
    .sum(min_count=10)  # évite jours incomplets
)
obs_daily = obs_daily.dropna()
obs_daily = obs_daily.where(obs_daily > 0)

print("time step médian (h):",
      obs.index.to_series().diff().median().total_seconds()/3600)

# Pour LE :
# obs_daily = obs["LE_J"].resample("D").mean()

# ============================================================
# 2. Charger CLASSIC
# ============================================================

file_classic = r"C:\Users\danyblanchet7\evspsbl_daily.nc"

ds = nc.Dataset(file_classic)

evap = ds.variables["evspsbl"][:,0,0]

time = ds.variables["time"][:]

units = ds.variables["time"].units

dates = nc.num2date(
    time,
    units,
    only_use_cftime_datetimes=False
)

dates = pd.to_datetime(dates)

classic = pd.Series(evap, index=dates)
classic = classic.where(classic > 0)

ds.close()

# ============================================================
# Conversions
# ============================================================

# Aprés vérification on a evspsbl est en kg m-2 s-1 !!
# --> mm/jour

classic = classic * 86400


# ============================================================
# Période commune
# ============================================================

common = pd.concat([classic, obs_daily], axis=1, sort=True)

common.columns = ["CLASSIC","Observation"]

common = common.dropna()


# ============================================================
# Statistiques
# ============================================================

corr = common.corr().iloc[0,1]
rmse = np.sqrt(np.mean((common.CLASSIC-common.Observation)**2))

print("Nombre de jours :",len(common))
print("Corrélation :",corr)
print("RMSE :",rmse)
print("CLASSIC mean:", classic.mean())
print("OBS mean:", obs_daily.mean())
print("Bias:", classic.mean() - obs_daily.mean())


# ============================================================
# Graphique
# ============================================================

plt.figure(figsize=(14,6))

plt.plot(common.index,
         common.CLASSIC,
         label="CLASSIC",
         linewidth=2)

plt.plot(common.index,
         common.Observation,
         label="Tour à flux",
         linewidth=1)

plt.legend()

plt.xlabel("Date")

plt.ylabel("ET (mm/jour)")

plt.title("Comparaison CLASSIC - Observations")

plt.grid(True)

plt.tight_layout()

plt.show()


