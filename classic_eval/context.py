#Objet partagé entre toutes les étapes : config + données + petits utilitaires.
import os
from .prepare import align


class Context:
    def __init__(self, cfg, obs, classic):
        self.cfg, self.obs, self.classic = cfg, obs, classic
        self._daily = {}

    def out(self, *parts):
        """Dossier de sortie (créé à la demande), ex. ctx.out('03_flux')."""
        path = os.path.join(self.cfg.output_dir, *parts)
        os.makedirs(path, exist_ok=True)
        return path

    def available(self, var):
        """True si la colonne obs ET la variable CLASSIC existent."""
        return var.obs in self.obs.columns and var.sim in self.classic

    def daily_perf(self, var):
        """DataFrame Date / OBS / SIM en moyennes journalières, toutes années (mis en cache)."""
        if var.obs not in self._daily:
            self._daily[var.obs] = align(self.obs, self.classic[var.sim], var.obs, var.sim,
                                         resolution="daily")
        return self._daily[var.obs]
