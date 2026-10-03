"""Source-aligned split-half reliability for single-cell perturbations.

This module implements the reliability definition used by Wang et al. (2026):
repeated matched perturbation/control split halves, Pearson agreement of the
two delta vectors, and Spearman--Brown correction.  Specificity is evaluated
separately as the squared cosine with the mean reliable perturbation response.

It is intentionally separate from the original ``similarity_and_signal_v1``
heuristic so historical CellForge runs remain reproducible while the method is
validated on real data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import numpy as np


class SplitHalfClass(str, Enum):
    SPECIFIC = "SPECIFIC"
    SHARED = "SHARED"
    UNRELIABLE = "UNRELIABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class SplitHalfConfig:
    """Explicit, source-aligned analysis parameters."""

    perturbation_column: str = "target_gene"
    control_column: str = "is_control"
    context_column: str = "context"
    min_cells: int = 8
    repeats: int = 100
    expressed_genes: int = 1000
    reliability_threshold: float = 0.5
    shared_cosine_threshold: float = 1.0 / np.sqrt(2.0)
    seed: int = 17
    method: str = "published_split_half_spearman_brown_v1"

    def __post_init__(self) -> None:
        if self.min_cells < 4 or self.repeats < 1 or self.expressed_genes < 1:
            raise ValueError("split-half minimums must be positive and min_cells >= 4")
        if not 0 <= self.reliability_threshold <= 1:
            raise ValueError("reliability_threshold must be in [0, 1]")
        if not 0 <= self.shared_cosine_threshold <= 1:
            raise ValueError("shared_cosine_threshold must be in [0, 1]")


@dataclass(frozen=True)
class SplitHalfRecord:
    perturbation: str
    context: str
    cells: int
    control_cells: int
    n_half: int
    median_split_correlation: float
    mean_split_correlation: float
    reliability: float
    response_magnitude: float
    shared_cosine: float | None
    shared_variance_fraction: float | None
    classification: SplitHalfClass
    bootstrap_classification: SplitHalfClass | None = None
    bootstrap_stability: float | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        if self.bootstrap_classification is not None:
            payload["bootstrap_classification"] = self.bootstrap_classification.value
        return payload


def _dense(x: Any) -> np.ndarray:
    return np.asarray(x.toarray() if hasattr(x, "toarray") else x, dtype=np.float32)


def _pearson(left: np.ndarray, right: np.ndarray) -> float:
    left = left - left.mean()
    right = right - right.mean()
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denom) if denom > 0 else 0.0


def _spearman_brown(correlation: float) -> float:
    denominator = 1.0 + correlation
    if abs(denominator) < 1e-12:
        return 0.0
    return float(np.clip(2.0 * correlation / denominator, 0.0, 1.0))


def _split_half(
    perturbation: np.ndarray,
    control: np.ndarray,
    *,
    n_half: int,
    repeats: int,
    seed: int,
) -> tuple[float, float, np.ndarray]:
    rng = np.random.default_rng(seed)
    correlations: list[float] = []
    deltas: list[np.ndarray] = []
    for _ in range(repeats):
        p = rng.permutation(len(perturbation))
        c = rng.permutation(len(control))
        delta_a = perturbation[p[:n_half]].mean(axis=0) - control[c[:n_half]].mean(axis=0)
        delta_b = perturbation[p[n_half : 2 * n_half]].mean(axis=0) - control[c[n_half : 2 * n_half]].mean(axis=0)
        correlations.append(_pearson(delta_a, delta_b))
        deltas.append((delta_a + delta_b) / 2.0)
    values = np.asarray(correlations, dtype=np.float64)
    return float(np.median(values)), float(np.mean(values)), np.asarray(deltas, dtype=np.float32)


def _classify(reliability: float, shared_cosine: float | None, config: SplitHalfConfig) -> SplitHalfClass:
    if reliability < config.reliability_threshold:
        return SplitHalfClass.UNRELIABLE
    if shared_cosine is not None and shared_cosine >= config.shared_cosine_threshold:
        return SplitHalfClass.SHARED
    return SplitHalfClass.SPECIFIC


def classify_anndata(adata: Any, config: SplitHalfConfig | None = None) -> tuple[SplitHalfRecord, ...]:
    """Classify every eligible perturbation in an AnnData object.

    The expression scale is treated as already processed.  This matches the
    published preprocessed scPerturBench contract; callers must record the
    scale in their run manifest rather than normalizing implicitly here.
    """

    config = config or SplitHalfConfig()
    for column in (config.perturbation_column, config.control_column, config.context_column):
        if column not in adata.obs.columns:
            raise ValueError(f"AnnData.obs is missing {column!r}")
    matrix = _dense(adata.X)
    contexts = adata.obs[config.context_column].astype(str).to_numpy()
    labels = adata.obs[config.perturbation_column].astype(str).to_numpy()
    controls = adata.obs[config.control_column].to_numpy(dtype=bool)
    records: list[dict[str, Any]] = []
    for context in sorted(set(contexts)):
        context_mask = contexts == context
        control = matrix[context_mask & controls]
        # Select genes from controls only, independent of perturbation effects
        # and split-half draws, as in the published top-expression mode.
        if control.shape[1] > config.expressed_genes:
            expression_order = np.argsort(control.mean(axis=0))[-config.expressed_genes :]
            context_matrix = matrix[:, expression_order]
            control = context_matrix[context_mask & controls]
        else:
            context_matrix = matrix
        for perturbation in sorted(set(labels[context_mask & ~controls])):
            pert = context_matrix[context_mask & ~controls & (labels == perturbation)]
            n_half = min(len(pert) // 2, len(control) // 2)
            limitations: list[str] = []
            if n_half < config.min_cells:
                records.append({
                    "perturbation": perturbation,
                    "context": context,
                    "cells": len(pert),
                    "control_cells": len(control),
                    "n_half": n_half,
                    "median_split_correlation": float("nan"),
                    "mean_split_correlation": float("nan"),
                    "reliability": 0.0,
                    "response_magnitude": float("nan"),
                    "shared_cosine": None,
                    "shared_variance_fraction": None,
                    "classification": SplitHalfClass.INSUFFICIENT_DATA,
                    "limitations": ("fewer than configured split-half cells",),
                })
                continue
            control_mean = control.mean(axis=0)
            response = pert.mean(axis=0) - control_mean
            median_r, mean_r, split_deltas = _split_half(
                pert,
                control,
                n_half=n_half,
                repeats=config.repeats,
                seed=config.seed + len(records),
            )
            records.append({
                "perturbation": perturbation,
                "context": context,
                "cells": len(pert),
                "control_cells": len(control),
                "n_half": n_half,
                "median_split_correlation": median_r,
                "mean_split_correlation": mean_r,
                "reliability": _spearman_brown(median_r),
                "response_magnitude": float(np.sqrt(np.mean(np.square(response)))),
                "shared_cosine": None,
                "shared_variance_fraction": None,
                "classification": None,
                "_response": response,
                "_split_deltas": split_deltas,
                "limitations": tuple(limitations),
            })

    reliable = [row for row in records if row["reliability"] >= config.reliability_threshold]
    axes: dict[str, np.ndarray] = {}
    for context in sorted(set(row["context"] for row in reliable)):
        effects = [row["_response"] for row in reliable if row["context"] == context]
        if effects:
            axes[context] = np.mean(np.stack(effects), axis=0)
    finalized: list[SplitHalfRecord] = []
    for row in records:
        axis = axes.get(row["context"])
        cosine = None
        if axis is not None and row.get("_response") is not None:
            cosine = _pearson(np.asarray(row["_response"]), axis)
            # cosine, not Pearson, is the published shared-axis statistic.
            left = np.asarray(row["_response"])
            denom = float(np.linalg.norm(left) * np.linalg.norm(axis))
            cosine = float(np.dot(left, axis) / denom) if denom > 0 else 0.0
        classification = row["classification"] or _classify(row["reliability"], cosine, config)
        finalized.append(
            SplitHalfRecord(
                perturbation=row["perturbation"],
                context=row["context"],
                cells=row["cells"],
                control_cells=row["control_cells"],
                n_half=row["n_half"],
                median_split_correlation=row["median_split_correlation"],
                mean_split_correlation=row["mean_split_correlation"],
                reliability=row["reliability"],
                response_magnitude=row["response_magnitude"],
                shared_cosine=cosine,
                shared_variance_fraction=None if cosine is None else float(cosine**2),
                classification=classification,
                limitations=tuple(row["limitations"]),
            )
        )
    return tuple(finalized)
