def select_year(df, year):

    return df[
        df["Date"].dt.year == year
    ]


def select_month(df, year, month):

    return df[
        (df["Date"].dt.year == year) &
        (df["Date"].dt.month == month)
    ]


def growing_season(df, year):

    return df[
        (df["Date"].dt.year == year) &
        (df["Date"].dt.month.between(5, 9))
    ]



def summer(df, year):

    return df[
        (df["Date"].dt.year == year) &
        (df["Date"].dt.month.between(6, 8))
    ]

def select_period(df, period, year, month=None):

    if period == "annual":
        return select_year(df, year)

    elif period == "growing_season":
        return growing_season(df, year)

    elif period == "summer":
        return summer(df, year)

    elif period == "month":
        return select_month(df, year, month)

    else:
        raise ValueError(f"Période inconnue : {period}")