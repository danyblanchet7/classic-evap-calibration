##plot
import matplotlib.pyplot as plt   
import matplotlib.pyplot as plt


def plot_calibration(data, variable):

    plt.figure(figsize=(12, 5))

    plt.plot(
        data["Date"],
        data["OBS"],
        label="Observations"
    )

    plt.plot(
        data["Date"],
        data["SIM"],
        label="CLASSIC"
    )

    plt.xlabel("Date")
    plt.ylabel(variable)
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()