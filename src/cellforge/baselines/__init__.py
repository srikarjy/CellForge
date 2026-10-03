"""Strong simple baselines under the shared prediction contract."""

from cellforge.baselines.models import (
    ControlMean,
    EmbeddingKNN,
    EmbeddingRidge,
    SeenPerturbationDelta,
    TrainMeanShift,
)

__all__ = [
    "ControlMean",
    "EmbeddingKNN",
    "EmbeddingRidge",
    "SeenPerturbationDelta",
    "TrainMeanShift",
]
