"""classic_eval : évaluation d'une simulation CLASSIC contre des observations de tour à flux.

Usage minimal :
    from classic_eval import EvalConfig, Period, run
    cfg = EvalConfig(obs_dir=..., classic_dir=..., output_dir=..., periods=[Period(...), ...])
    run(cfg)
"""
from .config import EvalConfig, Period, Variable
from .pipeline import run, ALL_STAGES

__all__ = ["EvalConfig", "Period", "Variable", "run", "ALL_STAGES"]
