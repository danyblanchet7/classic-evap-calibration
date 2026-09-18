import matplotlib.pyplot as plt


def plot_root_depth(root_df, output_path, start_year, end_year):

    print(f"... plotting root depth {start_year}-{end_year}")

    root_period = root_df[
        (root_df["Date"].dt.year >= start_year)
        & (root_df["Date"].dt.year <= end_year)
    ]

    plt.figure(figsize=(12, 5))

    # PFT 1
    plt.plot(
        root_period["Date"],
        root_period["PFT1"],
        marker="o",
        linewidth=1.5,
        label="PFT 1"
    )

    # PFT 8
    plt.plot(
        root_period["Date"],
        root_period["PFT8"],
        marker="o",
        linewidth=1.5,
        label="PFT 8"
    )

    plt.ylabel("Profondeur racinaire (m)")
    plt.xlabel("Date")
    plt.title(
        f"CLASSIC - Profondeur racinaire - {start_year}-{end_year}"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        output_path + f"root_depth_PFT1_PFT8_{start_year}_{end_year}.png",
        dpi=150
    )

    plt.close()

    print("Root depth plot saved.")