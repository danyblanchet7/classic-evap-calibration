##plot
import matplotlib.pyplot as plt   
import matplotlib.pyplot as plt

def plot_calibration(data, variable, period, units, output_path):

    plt.figure(figsize=(12, 5))

    plt.plot(
        data["Date"],
        data["OBS"],
        color = "blue",
        label="Observations"
    )

    plt.plot(
        data["Date"],
        data["SIM"],
        label="CLASSIC",
        color = "red",
    )

    plt.xlabel("Date")
    plt.ylabel(variable + " (" + units + ")")
    plt.legend()
    plt.grid()

    plt.tight_layout()
    filename = output_path + f"{variable}_{period}.png"

    plt.savefig(filename, dpi=300)
    plt.close()

    print(f"Graphique sauvegardé : {filename}")
