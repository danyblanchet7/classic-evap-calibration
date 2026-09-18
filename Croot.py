import netCDF4 as nc
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = (
    r"\\wsl.localhost\Ubuntu\home\danyblanchet7"
    r"\CLASSIC\outputFiles\Juvenile_Transient"
    r"\cRoot_monthly_perpft.nc"
)

OUTPUT_PATH = (
    r"C:\Users\danyblanchet7\Desktop\Data analysis\FM"
)


# ============================================================
# OUVERTURE
# ============================================================

dataset = nc.Dataset(FILE_PATH)

print("\n===== VARIABLES =====")
print(dataset.variables.keys())


# ============================================================
# DIMENSIONS
# ============================================================

print("\n===== DIMENSIONS =====")

for name, variable in dataset.variables.items():

    print(
        f"{name} : "
        f"dimensions = {variable.dimensions}, "
        f"shape = {variable.shape}"
    )


# ============================================================
# EXTRACTION
# ============================================================

croot = dataset.variables["cRoot"]
time = dataset.variables["time"]

print("\n===== cRoot =====")
print("Dimensions :", croot.dimensions)
print("Shape :", croot.shape)


# Dates
dates = nc.num2date(
    time[:],
    units=time.units,
    only_use_cftime_datetimes=False
)

dates = pd.to_datetime(dates)


# ============================================================
# EXTRACTION DES PFT
# ============================================================

# On suppose ici :
# time × pft × lat × lon

if croot.ndim == 4:

    values = croot[:, :, 0, 0]

else:

    raise ValueError(
        f"Structure inattendue : {croot.shape}"
    )


# ============================================================
# DATAFRAME
# ============================================================

data = {
    "Date": dates
}

for pft in range(values.shape[1]):

    data[f"PFT{pft + 1}"] = values[:, pft]

df = pd.DataFrame(data)

print("\n===== DONNÉES =====")
print(df.to_string(index=False))


# ============================================================
# STATISTIQUES
# ============================================================

print("\n===== STATISTIQUES =====")

for pft in df.columns[1:]:

    print(
        f"{pft} : "
        f"min = {df[pft].min():.4f}, "
        f"max = {df[pft].max():.4f}, "
        f"moyenne = {df[pft].mean():.4f}"
    )


# ============================================================
# GRAPHIQUE
# ============================================================

plt.figure(figsize=(12, 6))

for pft in df.columns[1:]:

    plt.plot(
        df["Date"],
        df[pft],
        linewidth=1.2,
        label=pft
    )

plt.xlabel("Date")
plt.ylabel("Root carbon (kg C m⁻²)")

plt.title(
    "CLASSIC - Root carbon by PFT"
)

plt.legend(
    ncol=3,
    fontsize=8
)

plt.grid(True, alpha=0.3)

plt.tight_layout()

output_file = (
    OUTPUT_PATH
    + r"\cRoot_monthly_perpft.png"
)

plt.savefig(
    output_file,
    dpi=150
)

plt.show()
plt.close()

dataset.close()

print("\nGraphique sauvegardé :")
print(output_file)