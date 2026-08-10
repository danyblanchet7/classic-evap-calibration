import xarray as xr
import os

# Dossier WSL accessible depuis Windows
base = r"\\wsl$\Ubuntu\home\classic_ops\kyoungho_calibration\CA-MonJ\outputFiles\Juvenile_Transient"

# Chargement des fichiers halfhourly
rsds = xr.open_dataset(os.path.join(base, "rsds_halfhourly.nc"))
rss  = xr.open_dataset(os.path.join(base, "rss_halfhourly.nc"))
rlds = xr.open_dataset(os.path.join(base, "rlds_halfhourly.nc"))
rls  = xr.open_dataset(os.path.join(base, "rls_halfhourly.nc"))

# Calculs physiques
rsus = rsds["rsds"] - rss["rss"]
rlus = rlds["rlds"] - rls["rls"]

# Construction des nouveaux datasets
ds_rsus = xr.Dataset({"rsus": rsus}, coords=rsds.coords)
ds_rlus = xr.Dataset({"rlus": rlus}, coords=rlds.coords)

# Écriture des fichiers NetCDF dans WSL
ds_rsus.to_netcdf(os.path.join(base, "rsus_halfhourly_calc.nc"))
ds_rlus.to_netcdf(os.path.join(base, "rlus_halfhourly_calc.nc"))

print("Fichiers créés dans WSL : rsus_halfhourly_calc.nc et rlus_halfhourly_calc.nc")
