"""Simple, fairly-tuned baselines that every advanced model must beat to matter.

Embedding baselines describe a perturbation by how the *target gene itself*
responded across the training perturbations (its column in the training
delta matrix), then regress or look up neighbours in that space. They use no
held-out data and no external annotation, so their information access is
exactly what is written in ``information_access``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

from cellforge.evaluation.contract import Predictions, gene_lookup, pseudobulk
from cellforge.splits import SplitColumns

if TYPE_CHECKING:
    from anndata import AnnData


class _Base:
    name = "base"
    information_access = ""

    def __init__(self, gene_symbol_column: str = "gene_symbol") -> None:
        self._symbol_column = gene_symbol_column
        self._fitted = False

    def fit(self, train: AnnData, columns: SplitColumns) -> None:
        pb = pseudobulk(train, columns)
        if not pb.perturbations:
            raise ValueError("Training data contains no eligible perturbations")
        self._genes = tuple(map(str, train.var_names))
        self._control = pb.control_mean
        self._train_perts = pb.perturbations
        self._train_deltas = pb.means - pb.control_mean
        self._mean_delta = self._train_deltas.mean(axis=0)
        self._gene_index = gene_lookup(train, self._symbol_column)
        self._fit_extra()
        self._fitted = True

    def _fit_extra(self) -> None:
        """Hook for models that need more than the mean shift."""

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        raise NotImplementedError

    def predict(self, perturbations: Sequence[str]) -> Predictions:
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")
        rows, covered = [], []
        for perturbation in perturbations:
            delta, ok = self._delta_for(str(perturbation))
            rows.append(self._control + delta)
            covered.append(ok)
        matrix = np.vstack(rows) if rows else np.empty((0, len(self._genes)))
        return Predictions(
            tuple(map(str, perturbations)), self._genes, matrix, self._control, tuple(covered)
        )


class ControlMean(_Base):
    name = "control_mean"
    information_access = "Training control cells only; predicts no change for every perturbation."

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        return np.zeros_like(self._control), True


class TrainMeanShift(_Base):
    name = "train_mean_shift"
    information_access = (
        "Training perturbed and control cells; predicts the average training effect "
        "for every perturbation regardless of its identity."
    )

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        return self._mean_delta, True


class SeenPerturbationDelta(_Base):
    """For context shift: reuse each perturbation's own effect from the training context."""

    name = "seen_perturbation_delta"
    information_access = (
        "Training-context effect of the same perturbation; falls back to the mean shift "
        "for perturbations absent from training."
    )

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        if perturbation in self._train_perts:
            return self._train_deltas[self._train_perts.index(perturbation)], True
        return self._mean_delta, False


class _EmbeddingBase(_Base):
    def __init__(self, n_components: int = 8, gene_symbol_column: str = "gene_symbol") -> None:
        super().__init__(gene_symbol_column)
        self.n_components = n_components

    def _fit_extra(self) -> None:
        # Each gene is described by its response across training perturbations.
        per_gene = self._train_deltas.T  # (n_genes, n_train_perturbations)
        centered = per_gene - per_gene.mean(axis=0, keepdims=True)
        k = max(1, min(self.n_components, min(centered.shape) - 1))
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        self._embedding = centered @ vt[:k].T  # (n_genes, k)
        rows = [(i, self._gene_index[p]) for i, p in enumerate(self._train_perts) if p in self._gene_index]
        if len(rows) < 2:
            raise ValueError("Fewer than 2 training perturbations map to measured genes")
        self._rows = np.array([i for i, _ in rows])
        self._train_features = self._embedding[[g for _, g in rows]]
        self._fit_model()

    def _fit_model(self) -> None:
        raise NotImplementedError

    def _features(self, perturbation: str) -> np.ndarray | None:
        index = self._gene_index.get(perturbation)
        return None if index is None else self._embedding[index]


class EmbeddingRidge(_EmbeddingBase):
    name = "embedding_ridge"
    information_access = (
        "Training perturbed and control cells; represents an unseen perturbation by its target "
        "gene's response pattern across training perturbations (no external annotation)."
    )

    def __init__(
        self, alpha: float = 1.0, n_components: int = 8, gene_symbol_column: str = "gene_symbol"
    ) -> None:
        super().__init__(n_components, gene_symbol_column)
        self.alpha = alpha

    def _fit_model(self) -> None:
        x = self._train_features
        y = self._train_deltas[self._rows]
        self._x_mean, self._y_mean = x.mean(axis=0), y.mean(axis=0)
        xc, yc = x - self._x_mean, y - self._y_mean
        gram = xc.T @ xc + self.alpha * np.eye(xc.shape[1])
        self._weights = np.linalg.solve(gram, xc.T @ yc)

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        features = self._features(perturbation)
        if features is None:
            return self._mean_delta, False
        return (features - self._x_mean) @ self._weights + self._y_mean, True


class EmbeddingKNN(_EmbeddingBase):
    name = "embedding_knn"
    information_access = EmbeddingRidge.information_access

    def __init__(
        self, k: int = 5, n_components: int = 8, gene_symbol_column: str = "gene_symbol"
    ) -> None:
        super().__init__(n_components, gene_symbol_column)
        self.k = k

    def _fit_model(self) -> None:
        norms = np.linalg.norm(self._train_features, axis=1, keepdims=True)
        self._unit = self._train_features / np.where(norms == 0, 1.0, norms)

    def _delta_for(self, perturbation: str) -> tuple[np.ndarray, bool]:
        features = self._features(perturbation)
        if features is None:
            return self._mean_delta, False
        norm = np.linalg.norm(features)
        similarity = self._unit @ (features / (norm if norm else 1.0))
        nearest = np.argsort(-similarity)[: self.k]
        return self._train_deltas[self._rows[nearest]].mean(axis=0), True
