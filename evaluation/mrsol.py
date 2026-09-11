import os
import pandas as pd
import matplotlib.pyplot as plt
import netCDF4 as nc


def plot_soil_water_layers(
    CLASSIC_PATH_FM_K,
    OUTPUT_SOIL,
    YEAR_SOIL
):

    # dossier de sortie
    os.makedirs(
        OUTPUT_SOIL,
        exist_ok=True
    )

    # ------------------------------------------------------
    # Recharger mrsol_daily.nc
    # ------------------------------------------------------

    mrsol_path = CLASSIC_PATH_FM_K + "mrsol_daily.nc"

    ds_mrsol = nc.Dataset(mrsol_path)

    raw = ds_mrsol.variables["mrsol"]
    # (time, layer, lat, lon)

    time = ds_mrsol.variables["time"]

    dates = nc.num2date(
        time[:],
        units=time.units,
        calendar=getattr(
            time,
            "calendar",
            "standard"
        )
    )

    # ------------------------------------------------------
    # Convertir les dates en DataFrame
    # ------------------------------------------------------

    df = pd.DataFrame({
        "Date": [
            pd.Timestamp(d.isoformat())
            for d in dates
        ]
    })

    # ------------------------------------------------------
    # Nombre de couches
    # ------------------------------------------------------

    n_layers = raw.shape[1]

    # ------------------------------------------------------
    # Tracer chaque couche
    # ------------------------------------------------------

    for layer in range(n_layers):

        # extraire la couche
        df_layer = df.copy()

        df_layer["mrsol"] = raw[
            :, layer, 0, 0
        ]

        # filtrer l'année
        df_annual = df_layer[
            df_layer["Date"].dt.year == YEAR_SOIL
        ]

        # tracer
        plt.figure(
            figsize=(10, 5)
        )

        plt.plot(
            df_annual["Date"],
            df_annual["mrsol"],
            linewidth=1.5
        )

        plt.ylabel("mrsol (kg/m²)")

        plt.title(
            f"CLASSIC - Eau du sol - "
            f"Couche {layer} - Annuel {YEAR_SOIL}"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        # enregistrer
        outpath = os.path.join(
            OUTPUT_SOIL,
            f"mrsol_layer{layer}_annual_{YEAR_SOIL}.png"
        )

        plt.savefig(
            outpath,
            dpi=150
        )

        plt.close()

    # fermer le fichier NetCDF
    ds_mrsol.close()