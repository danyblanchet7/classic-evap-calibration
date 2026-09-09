import pandas as pd
import matplotlib.pyplot as plt

from evaluation.temporal import (
    to_daily_mean,
    to_monthly_mean
)


# ==========================================================
# STYLE GRAPHIQUE
# ==========================================================

OBS_COLOR = "red"
SIM_COLOR = "blue"

FONT = "Arial"

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9
})


# ==========================================================
# GRAPHIQUE JOURNALIER
# ==========================================================

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

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(
        data["Date"],
        data["OBS"],
        color=OBS_COLOR,
        linewidth=1.2,
        label="Observations"
    )

    ax.plot(
        data["Date"],
        data["SIM"],
        color=SIM_COLOR,
        linewidth=1.2,
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

    ax.legend(
        frameon=True
    )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150,
        facecolor="white"
    )
    plt.close()

    return data


# ==========================================================
# GRAPHIQUE MENSUEL
# ==========================================================

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

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(
        data["Date"],
        data["OBS"],
        color=OBS_COLOR,
        linewidth=1.5,
        label="Observations"
    )

    ax.plot(
        data["Date"],
        data["SIM"],
        color=SIM_COLOR,
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

    ax.legend(
        frameon=True
    )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150,
        facecolor="white"
    )
    plt.close()

    return data