import matplotlib.pyplot as plt


def plot_snow_variables(
    classic,
    snow_variables,
    output_path
):

    print("... plotting snow variables")

    fig, axes = plt.subplots(
        len(snow_variables),
        1,
        figsize=(12, 3 * len(snow_variables)),
        sharex=True
    )

    # Si une seule variable
    if len(snow_variables) == 1:
        axes = [axes]

    for ax, (var, label) in zip(
        axes,
        snow_variables.items()
    ):

        df = classic[var]

        ax.plot(
            df["Date"],
            df[var],
            linewidth=1
        )

        ax.set_ylabel(label)
        ax.set_title(f"CLASSIC - {var}")

        ax.grid(
            True,
            alpha=0.3
        )

    axes[-1].set_xlabel("Date")

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=150,
        facecolor="white"
    )

    plt.close()

    print("Snow plot saved.")