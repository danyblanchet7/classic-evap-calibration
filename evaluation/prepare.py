import pandas as pd

import pandas as pd


def prepare_comparison(obs, sim, obs_variable, sim_variable):

    obs = obs[["Date", obs_variable]].copy()
    sim = sim[["Date", sim_variable]].copy()

    sim = sim.rename(columns={sim_variable: "SIM"})
    obs = obs.rename(columns={obs_variable: "OBS"})

    perf = pd.merge(
        obs,
        sim,
        on="Date",
        how="inner"
    )

    return perf.dropna()