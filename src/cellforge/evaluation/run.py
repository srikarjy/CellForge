"""Leakage-safe evaluation of any model that follows the prediction contract."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from cellforge.evaluation.contract import PerturbationModel, pseudobulk
from cellforge.splits import SplitColumns, SplitManifest, apply_split, check_leakage

if TYPE_CHECKING:
    from anndata import AnnData


def delta_pearson(predicted: np.ndarray, observed: np.ndarray) -> float:
    """Pearson correlation of change-from-control; NaN when either vector is constant."""

    if predicted.std() == 0 or observed.std() == 0:
        return float("nan")
    return float(np.corrcoef(predicted, observed)[0, 1])


def delta_mse(predicted: np.ndarray, observed: np.ndarray) -> float:
    return float(np.mean((predicted - observed) ** 2))


@dataclass(frozen=True)
class PerturbationScore:
    perturbation: str
    cells: int
    pearson_delta: float
    mse_delta: float
    covered: bool


@dataclass(frozen=True)
class EvaluationResult:
    model: str
    information_access: str
    partition: str
    split_sha256: str
    scores: tuple[PerturbationScore, ...]
    model_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def coverage(self) -> float:
        return float(np.mean([s.covered for s in self.scores])) if self.scores else float("nan")

    @property
    def undefined_pearson(self) -> int:
        return sum(np.isnan(s.pearson_delta) for s in self.scores)

    @property
    def mean_pearson_delta(self) -> float:
        values = [s.pearson_delta for s in self.scores if not np.isnan(s.pearson_delta)]
        return float(np.mean(values)) if values else float("nan")

    @property
    def mean_mse_delta(self) -> float:
        return float(np.mean([s.mse_delta for s in self.scores])) if self.scores else float("nan")


def evaluate_model(
    adata: AnnData,
    manifest: SplitManifest,
    model: PerturbationModel,
    columns: SplitColumns | None = None,
    partition: str = "test",
) -> EvaluationResult:
    """Verify the split, fit on train only, and score against the held-out partition."""

    columns = columns or SplitColumns()
    check_leakage(adata, manifest, columns).raise_for_errors()
    model.fit(apply_split(adata, manifest, "train"), columns)

    held_out = pseudobulk(apply_split(adata, manifest, partition), columns)
    predictions = model.predict(held_out.perturbations)
    predictions.validate()
    if predictions.perturbations != held_out.perturbations:
        raise ValueError("Model predicted a different perturbation set or order than requested")
    if predictions.genes != tuple(map(str, adata.var_names)):
        raise ValueError("Model gene order does not match the dataset")

    predicted_delta = predictions.mean_expression - predictions.control_mean
    observed_delta = held_out.means - held_out.control_mean
    scores = tuple(
        PerturbationScore(
            perturbation=name,
            cells=held_out.cell_counts[i],
            pearson_delta=delta_pearson(predicted_delta[i], observed_delta[i]),
            mse_delta=delta_mse(predicted_delta[i], observed_delta[i]),
            covered=predictions.covered[i],
        )
        for i, name in enumerate(held_out.perturbations)
    )
    metadata = {}
    provenance = getattr(model, "provenance", None)
    if callable(provenance):
        metadata = provenance(manifest.sha256, tuple(score.perturbation for score in scores))
    return EvaluationResult(model.name, model.information_access, partition, manifest.sha256, scores, metadata)


def select_by_validation(
    adata: AnnData,
    manifest: SplitManifest,
    factory: Callable[..., PerturbationModel],
    grid: Sequence[dict[str, Any]],
    columns: SplitColumns | None = None,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], float]]]:
    """Pick hyperparameters on the validation partition only; the test set is never touched."""

    if not grid:
        raise ValueError("Hyperparameter grid is empty")
    results = []
    for params in grid:
        result = evaluate_model(adata, manifest, factory(**params), columns, partition="val")
        results.append((params, result.mean_pearson_delta))
    usable = [(p, s) for p, s in results if not np.isnan(s)]
    if not usable:
        raise ValueError("Every configuration produced an undefined validation score")
    return max(usable, key=lambda item: item[1])[0], results
