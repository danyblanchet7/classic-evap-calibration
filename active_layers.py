import netCDF4 as nc
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = (
    r"\\wsl.localhost\Ubuntu\home\danyblanchet7"
    r"\CLASSIC\outputFiles\Juvenile_Transient"
    r"\actlyrmax_monthly.nc"
)

OUTPUT_PATH = (
    r"C:\Users\danyblanchet7\Desktop\Data analysis\FM"
)


# ============================================================
# OUVERTURE DU FICHIER
# ============================================================

print("\n===== OUVERTURE DU FICHIER =====")

dataset = nc.Dataset(FILE_PATH)

print("Variables disponibles :")
print(dataset.variables.keys())


# ============================================================
# INFORMATIONS SUR LES VARIABLES
# ============================================================

print("\n===== DIMENSIONS DES VARIABLES =====")

for name, variable in dataset.variables.items():

    print(
        f"{name} : "
        f"dimensions = {variable.dimensions}, "
        f"shape = {variable.shape}"
    )


# ============================================================
# EXTRACTION DE ACTLYRMAX
# ============================================================

actlyrmax = dataset.variables["actlyrmax"]
time = dataset.variables["time"]


print("\n===== ACTLYRMAX =====")

print("Dimensions :", actlyrmax.dimensions)
print("Shape :", actlyrmax.shape)

# Conversion du temps CLASSIC → dates
dates = nc.num2date(
    time[:],
    units=time.units,
    only_use_cftime_datetimes=False
)

dates = pd.to_datetime(dates)


# ============================================================
# EXTRACTION DES VALEURS
# ============================================================

# Cas classique : time, lat, lon
if actlyrmax.ndim == 3:

    values = actlyrmax[:, 0, 0]

# Cas où il n'y a que time
elif actlyrmax.ndim == 1:

    values = actlyrmax[:]

else:

    raise ValueError(
        f"Structure inattendue pour actlyrmax : "
        f"{actlyrmax.shape}"
    )


# Création du DataFrame
df = pd.DataFrame({
    "Date": dates,
    "actlyrmax": values
})


# ============================================================
# NETTOYAGE
# ============================================================

df = df.sort_values("Date")

print("\n===== DONNÉES =====")

print(df.to_string(index=False))


# ============================================================
# STATISTIQUES
# ============================================================

print("\n===== STATISTIQUES =====")

print("Nombre de valeurs :", len(df))
print("Minimum :", df["actlyrmax"].min())
print("Maximum :", df["actlyrmax"].max())
print("Moyenne :", df["actlyrmax"].mean())

print("\nVariation entre première et dernière valeur :")

variation = (
    df["actlyrmax"].iloc[-1]
    - df["actlyrmax"].iloc[0]
)

print(variation)


# ============================================================
# GRAPHIQUE
# ============================================================

plt.figure(figsize=(12, 5))

plt.plot(
    df["Date"],
    df["actlyrmax"],
    marker="o",
    linewidth=1.5
)

plt.xlabel("Date")
plt.ylabel("Active layer maximum depth (m)")

plt.title(
    "CLASSIC - Maximum annual active layer depth"
)

plt.grid(True, alpha=0.3)

plt.tight_layout()


# ============================================================
# SAUVEGARDE
# ============================================================

output_file = (
    OUTPUT_PATH
    + r"\actlyrmax_annually.png"
)

plt.savefig(
    output_file,
    dpi=150
)

plt.show()
plt.close()

print("\nGraphique sauvegardé :")
print(output_file)


# ============================================================
# FERMETURE
# ============================================================

dataset.close()

print("\n===== TERMINÉ =====")