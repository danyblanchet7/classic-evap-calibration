def select_month(df, year, month):

    return df[
        (df["Date"].dt.year == year) &
        (df["Date"].dt.month == month)
    ]


def select_year(df, year):

    return df[
        df["Date"].dt.year == year
    ]


def growing_season(df, year):

    return df[
        (df["Date"].dt.year == year) &
        (df["Date"].dt.month.between(5, 9))
    ]