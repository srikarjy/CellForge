"""The prediction contract shared by baselines and advanced models.

A model predicts a *mean expression profile* per perturbation, on the same scale
as the ``X`` it was trained on. The evaluator compares predicted and observed
changes relative to control, so models never see held-out cells or controls.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np
import pandas as pd

from cellforge.splits import SplitColumns

if TYPE_CHECKING:
    from anndata import AnnData


@dataclass(frozen=True)
class Predictions:
    perturbations: tuple[str, ...]
    genes: tuple[str, ...]
    mean_expression: np.ndarray  # (n_perturbations, n_genes)
    control_mean: np.ndarray  # (n_genes,) reference the model used for "no change"
    covered: tuple[bool, ...]  # False where the model had no information and fell back

    def validate(self) -> None:
        expected = (len(self.perturbations), len(self.genes))
        if self.mean_expression.shape != expected:
            raise ValueError(f"Prediction shape {self.mean_expression.shape} != {expected}")
        if self.control_mean.shape != (len(self.genes),):
            raise ValueError("control_mean must have one value per gene")
        if len(self.covered) != len(self.perturbations):
            raise ValueError("covered must have one flag per perturbation")
        if not (np.isfinite(self.mean_expression).all() and np.isfinite(self.control_mean).all()):
            raise ValueError("Predictions contain non-finite values")


class PerturbationModel(Protocol):
    name: str
    information_access: str  # plain-language statement of what the model may see

    def fit(self, train: AnnData, columns: SplitColumns) -> None: ...

    def predict(self, perturbations: Sequence[str]) -> Predictions: ...


@dataclass(frozen=True)
class Pseudobulk:
    control_mean: np.ndarray
    perturbations: tuple[str, ...]
    means: np.ndarray  # (n_perturbations, n_genes)
    cell_counts: tuple[int, ...]


def _mean_rows(x, positions: np.ndarray) -> np.ndarray:
    return np.asarray(x[positions].mean(axis=0), dtype=np.float64).ravel()


def pseudobulk(adata: AnnData, columns: SplitColumns) -> Pseudobulk:
    """Mean expression of controls and of each eligible single-target perturbation."""

    obs = adata.obs
    is_control = obs[columns.control].to_numpy(dtype=bool)
    if not is_control.any():
        raise ValueError("No control cells available to define the no-change reference")
    eligible = (obs[columns.assignment_class] == columns.eligible_class).to_numpy() & ~is_control
    perts = obs[columns.perturbation].astype(str).to_numpy()
    table = pd.DataFrame({"position": np.flatnonzero(eligible), "pert": perts[eligible]})
    groups = {p: g.to_numpy() for p, g in table.groupby("pert")["position"]}
    names = tuple(sorted(groups))
    means = (
        np.vstack([_mean_rows(adata.X, groups[p]) for p in names])
        if names
        else np.empty((0, adata.n_vars))
    )
    return Pseudobulk(
        control_mean=_mean_rows(adata.X, np.flatnonzero(is_control)),
        perturbations=names,
        means=means,
        cell_counts=tuple(len(groups[p]) for p in names),
    )


def gene_lookup(adata: AnnData, symbol_column: str = "gene_symbol") -> dict[str, int]:
    """Map gene symbol (or var name if there is no symbol column) to its column index."""

    names = adata.var[symbol_column] if symbol_column in adata.var.columns else adata.var_names
    lookup: dict[str, int] = {}
    for index, name in enumerate(map(str, names)):
        lookup.setdefault(name, index)
    return lookup
