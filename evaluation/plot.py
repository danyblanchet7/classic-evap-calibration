##plot
import matplotlib.pyplot as plt   
import matplotlib.pyplot as plt
import os 

def plot_calibration(data, variable, period):

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
    os.makedirs("result", exist_ok=True)
    filename = f"result/{variable}_{period}.png"
    plt.savefig(filename)
    plt.close()  
    plt.show()