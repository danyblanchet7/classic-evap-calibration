import netCDF4 as nc
import pandas as pd
import matplotlib.pyplot as plt



# CHARGEMENT D'UNE SORTIE MENSUELLE CLASSIC

def load_monthly_output(
    file_path,
    variable
):

    ds = nc.Dataset(file_path)

    data = ds.variables[variable][:]

    time = ds.variables["time"]

    dates = nc.num2date(
        time[:],
        units=time.units,
        calendar=getattr(
            time,
            "calendar",
            "standard"
        )
    )

    dates = pd.to_datetime(
        [d.isoformat() for d in dates]
    )

    df = pd.DataFrame({
        "Date": dates,
        variable: data[:, 0, 0]
    })

    ds.close()

    return df



# OBSERVATIONS -> MENSUEL


def to_monthly_mean(df, variable):

    df = df.copy()

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    return (
        df
        .set_index("Date")[variable]
        .resample("1ME")
        .mean()
        .reset_index()
    )



# GRAPHIQUE MENSUEL


def plot_monthly_timeseries(
    obs,
    sim_monthly,
    obs_variable,
    sim_variable,
    output_path,
    title=None
):

    # OBSERVATIONS -> mensuel
    obs_monthly = to_monthly_mean(
        obs,
        obs_variable
    )

    obs_monthly = obs_monthly.rename(
        columns={
            obs_variable: "OBS"
        }
    )

    # CLASSIC -> déjà mensuel
    sim_monthly = sim_monthly.rename(
        columns={
            sim_variable: "SIM"
        }
    )

    data = pd.merge(
        obs_monthly,
        sim_monthly[
            ["Date", "SIM"]
        ],
        on="Date",
        how="inner"
    )

    # Graphique
    fig, ax = plt.subplots(
        figsize=(12, 4)
    )

    ax.plot(
        data["Date"],
        data["OBS"],
        color="red",
        linewidth=1.5,
        label="Observations"
    )

    ax.plot(
        data["Date"],
        data["SIM"],
        color="blue",
        linewidth=1.5,
        label="CLASSIC"
    )

    ax.set_xlabel("Date")
    ax.set_ylabel(obs_variable)

    if title is not None:
        ax.set_title(title)

    ax.grid(
        True,
        alpha=0.25,
        linewidth=0.7
    )

    ax.legend()

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=150,
        facecolor="white"
    )

    plt.close()

    return data



# ANALYSE MENSUELLE CLASSIC


def analyze_monthly_outputs(
    obs,
    classic_path,
    output_path
):

    # H


    hfss_file = classic_path + "hfss_monthly.nc"

    hfss_monthly = load_monthly_output(
        hfss_file,
        "hfss"
    )

    plot_monthly_timeseries(
        obs=obs,
        sim_monthly=hfss_monthly,
        obs_variable="H_J",
        sim_variable="hfss",
        output_path=output_path
        + "H_monthly_all_years.png",
        title="H Évolution mensuelle sur toute la période"
    )



    # LE
 

    hfls_file = classic_path + "hfls_monthly.nc"

    hfls_monthly = load_monthly_output(
        hfls_file,
        "hfls"
    )

    plot_monthly_timeseries(
        obs=obs,
        sim_monthly=hfls_monthly,
        obs_variable="LE_J",
        sim_variable="hfls",
        output_path=output_path
        + "LE_monthly_all_years.png",
        title="LE Évolution mensuelle sur toute la période"
    )