import pandas as pd


def to_hourly_mean(df, variable):

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    return (
        df.set_index("Date")[variable]
        .resample("1h")
        .mean()
        .reset_index()
    )


def to_daily_mean(df, variable):

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    return (
        df.set_index("Date")[variable]
        .resample("1D")
        .mean()
        .reset_index()
    )


def to_monthly_mean(df, variable):

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    return (
        df.set_index("Date")[variable]
        .resample("1ME")
        .mean()
        .reset_index()
    )


def match_time_resolution(
    obs,
    obs_variable,
    sim_resolution
):

    if sim_resolution == "half-hourly":

        return obs.copy()

    elif sim_resolution == "hourly":

        return to_hourly_mean(
            obs,
            obs_variable
        )

    elif sim_resolution == "daily":

        return to_daily_mean(
            obs,
            obs_variable
        )

    else:

        raise ValueError(
            f"Résolution inconnue : {sim_resolution}"
        )