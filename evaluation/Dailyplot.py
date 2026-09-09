import pandas as pd
import matplotlib.pyplot as plt

from evaluation.temporal import (
    to_daily_mean,
    to_monthly_mean
)


def plot_daily_timeseries(
    obs,
    sim,
    obs_variable,
    sim_variable,
    output_path,
    title=None
):

    obs_daily = to_daily_mean(obs, obs_variable)
    sim_daily = to_daily_mean(sim, sim_variable)

    obs_daily = obs_daily.rename(
        columns={obs_variable: "OBS"}
    )

    sim_daily = sim_daily.rename(
        columns={sim_variable: "SIM"}
    )

    data = pd.merge(
        obs_daily,
        sim_daily,
        on="Date",
        how="inner"
    )

    plt.figure(figsize=(16, 6))

    plt.plot(
        data["Date"],
        data["OBS"],
        label="Observations",
        linewidth=0.8
    )

    plt.plot(
        data["Date"],
        data["SIM"],
        label="CLASSIC",
        linewidth=0.8
    )

    plt.xlabel("Date")
    plt.ylabel(obs_variable)

    if title is not None:
        plt.title(title)

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    plt.close()

    return data


def plot_monthly_timeseries(
    obs,
    sim,
    obs_variable,
    sim_variable,
    output_path,
    title=None
):

    obs_monthly = to_monthly_mean(obs, obs_variable)
    sim_monthly = to_monthly_mean(sim, sim_variable)

    obs_monthly = obs_monthly.rename(
        columns={obs_variable: "OBS"}
    )

    sim_monthly = sim_monthly.rename(
        columns={sim_variable: "SIM"}
    )

    data = pd.merge(
        obs_monthly,
        sim_monthly,
        on="Date",
        how="inner"
    )

    plt.figure(figsize=(16, 6))

    plt.plot(
        data["Date"],
        data["OBS"],
        label="Observations",
        linewidth=1.2
    )

    plt.plot(
        data["Date"],
        data["SIM"],
        label="CLASSIC",
        linewidth=1.2
    )

    plt.xlabel("Date")
    plt.ylabel(obs_variable)

    if title is not None:
        plt.title(title)

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    plt.close()

    return data