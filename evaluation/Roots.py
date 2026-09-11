import matplotlib.pyplot as plt


def plot_root_depth(
    root_df,
    output_path,
    start_year,
    end_year
):

    print(
        f"... plotting root depth "
        f"{start_year}-{end_year}"
    )

    # Sélection de la période
    root_period = root_df[
        (root_df["Date"].dt.year >= start_year)
        & (root_df["Date"].dt.year <= end_year)
    ]

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        root_period["Date"],
        root_period["rootdpth"],
        marker="o",
        linewidth=1.5
    )

    plt.ylabel(
        "Profondeur racinaire (m)"
    )

    plt.xlabel(
        "Date"
    )

    plt.title(
        f"CLASSIC - Profondeur racinaire - "
        f"{start_year}-{end_year}"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        output_path
        + f"root_depth_{start_year}_{end_year}.png",
        dpi=150
    )

    plt.close()

    print("Root depth plot saved.")