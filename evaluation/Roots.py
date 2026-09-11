import matplotlib.pyplot as plt


# PROFONDEUR RACINAIRE


def plot_root_depth(
    root_df,
    output_path,
    year
):

    print(f"... plotting root depth {year}")


    # Sélection de l'année

    root_year = root_df[
        root_df["Date"].dt.year == year
    ]


    plt.figure(
        figsize=(10, 5)
    )

    plt.plot(
        root_year["Date"],
        root_year["rootdpth"],
        marker="o",
        linewidth=2
    )

    plt.ylabel(
        "Profondeur racinaire (m)"
    )

    plt.xlabel(
        "Date"
    )

    plt.title(
        f"CLASSIC - Profondeur racinaire - {year}"
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        output_path
        + f"root_depth_annual_{year}.png",
        dpi=150
    )

    plt.close()
    print("Root depth plots saved.")