import netCDF4
import matplotlib.pyplot as plt
import pandas as pd

# ============================================================
# CHEMINS
# ============================================================

OBS_PATH = r"C:\Users\danyblanchet7\Desktop\Data analysis\data\snow_database_FM_23_25(in).csv"

CLASSIC_PATH = r"\\wsl.localhost\Ubuntu\home\danyblanchet7\CLASSIC\outputFiles\Juvenile_Transient\\"

# ============================================================
# OBSERVATIONS
# ============================================================

obs = pd.read_csv(OBS_PATH)

obs["Date"] = pd.to_datetime(
    obs["time"],
    format="mixed"
)

# ============================================================
# ISOLER LG ET CAN
# ============================================================

obs_LG = obs[obs["site"] == "LG"].copy()
obs_CAN = obs[obs["site"] == "CAN"].copy()

# ============================================================
# PÉRIODE
# ============================================================

start_date = "2023-10-01"
end_date = "2025-05-31"

obs_LG = obs_LG[
    (obs_LG["Date"] >= start_date) &
    (obs_LG["Date"] < "2025-06-01")
]

obs_CAN = obs_CAN[
    (obs_CAN["Date"] >= start_date) &
    (obs_CAN["Date"] < "2025-06-01")
]

# ============================================================
# MOYENNE JOURNALIÈRE LG + CAN
# ============================================================

LG_daily = (
    obs_LG
    .set_index("Date")["snow_depth"]
    .resample("1D")
    .mean()
)

CAN_daily = (
    obs_CAN
    .set_index("Date")["snow_depth"]
    .resample("1D")
    .mean()
)

# Moyenne LG + CAN
obs_mean = pd.concat(
    [LG_daily, CAN_daily],
    axis=1
)

obs_mean.columns = ["LG", "CAN"]

obs_mean["OBS_mean"] = obs_mean[["LG", "CAN"]].mean(axis=1)

# ============================================================
# CLASSIC : SNOW DEPTH
# ============================================================

classic_snd = netCDF4.Dataset(
    CLASSIC_PATH + "snd_daily.nc"
)

time = classic_snd.variables["time"][:]

# Extraction du seul point spatial
snd = classic_snd.variables["snd"][:, 0, 0]

print("Dimensions time :", time.shape)
print("Dimensions snd  :", classic_snd.variables["snd"].shape)

# Conversion du temps CLASSIC
classic_dates = netCDF4.num2date(
    time,
    classic_snd.variables["time"].units,
    calendar=classic_snd.variables["time"].calendar
)

classic_snd_df = pd.DataFrame({
    "Date": [pd.Timestamp(str(date)) for date in classic_dates],
    "snd_cm": snd * 100
})

# Garder 2023-10-01 → 2025-05-31
classic_snd_df = classic_snd_df[
    (classic_snd_df["Date"] >= "2023-10-01") &
    (classic_snd_df["Date"] < "2025-06-01")
]

# ============================================================
# COMPARAISON OBS VS CLASSIC
# ============================================================

fig, ax = plt.subplots(figsize=(14, 6))

# LG
ax.plot(
    obs_mean.index,
    obs_mean["LG"],
    color="#5DADE2",
    linewidth=1,
    label="OBS JUVENILE SITE LG"
)

# CAN
ax.plot(
    obs_mean.index,
    obs_mean["CAN"],
    color="#154360",
    linewidth=1,
    label="OBS JUVENILE SITE CAN"
)

# Moyenne LG + CAN
ax.plot(
    obs_mean.index,
    obs_mean["OBS_mean"],
    color="blue",
    linewidth=2,
    label="OBS - mean LG + CAN"
)

# CLASSIC
ax.plot(
    classic_snd_df["Date"],
    classic_snd_df["snd_cm"],
    color="red",
    linewidth=1,
    label="CLASSIC"
)

ax.set_xlabel("Date")
ax.set_ylabel("Snow depth (cm)")

ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()