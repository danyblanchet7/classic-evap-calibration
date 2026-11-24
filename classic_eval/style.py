"""Conventions graphiques communes à tout le package.

CONVENTION : observations = GRIS FONCÉ (noir adouci), simulations CLASSIC = BLEU, partout.
Pour changer les couleurs de tout le package, modifier uniquement ce fichier.
"""
import os
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

OBS_COLOR = "#4d4d4d"
SIM_COLOR = "#1f5fbf"
OBS_LABEL = "Observations"
SIM_LABEL = "CLASSIC"
OBS_GREYS = ("#b3b3b3", "#7f7f7f")   # nuances de gris : sous-séries d'obs (ex. sites LG / CAN)


def setup():
    """Réglages matplotlib globaux (appelé une fois par run())."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "axes.grid": True, "grid.alpha": 0.3,
    })


def plot_obs_sim(ax, x, obs, sim, lw=1.2, marker=None, ms=3):
    """Trace obs (noir) et sim (rouge) sur le même axe."""
    ax.plot(x, obs, color=OBS_COLOR, lw=lw, marker=marker, ms=ms, label=OBS_LABEL)
    ax.plot(x, sim, color=SIM_COLOR, lw=lw, marker=marker, ms=ms, label=SIM_LABEL)


def concise_dates(ax):
    """Axe des x en dates lisibles, quelle que soit la longueur de la période."""
    loc = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def save(fig, path, dpi=150):
    """Enregistre la figure (crée le dossier si besoin) puis la ferme."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"   figure : {path}")
    return path
