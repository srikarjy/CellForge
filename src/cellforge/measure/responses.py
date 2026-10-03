"""Transparent, deterministic response summaries for perturbation screens.

This module intentionally computes summaries only. Differential-expression and
perturbation-space methods from pertpy can be adopted behind this contract once
the optional dependency is available; the table keeps method/config metadata
so those implementations remain comparable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from cellforge.splits import SplitColumns, dataset_fingerprint

if TYPE_CHECKING:
    from anndata import AnnData


@dataclass(frozen=True)
class MeasurementConfig:
    """Explicit choices for response measurement and eligibility."""

    columns: SplitColumns = field(default_factory=SplitColumns)
    context_column: str = "context"
    min_cells: int = 20
    min_controls: int = 20
    top_k_genes: int = 20
    method: str = "mean_delta_v1"

    def __post_init__(self) -> None:
        if self.min_cells < 1 or self.min_controls < 1:
            raise ValueError("minimum cell counts must be positive")
        if self.top_k_genes < 1:
            raise ValueError("top_k_genes must be positive")


@dataclass(frozen=True)
class PerturbationResponse:
    perturbation: str
    context: str
    cells: int
    control_cells: int
    response_signal: float
    noise_rms: float
    effect_magnitude: float
    top_genes: tuple[str, ...]
    delta: tuple[float, ...]
    eligible: bool
    limitations: tuple[str, ...] = ()

    @property
    def signal_to_noise(self) -> float:
        return self.response_signal / self.noise_rms if self.noise_rms > 0 else float("inf")


@dataclass(frozen=True)
class MeasurementTable:
    dataset_fingerprint: str
    config: dict[str, Any]
    genes: tuple[str, ...]
    responses: tuple[PerturbationResponse, ...]
    artifact_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_fingerprint": self.dataset_fingerprint,
            "config": self.config,
            "genes": list(self.genes),
            "responses": [asdict(response) for response in self.responses],
            "artifact_sha256": self.artifact_sha256,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def _mean(x: Any, positions: np.ndarray) -> np.ndarray:
    return np.asarray(x[positions].mean(axis=0), dtype=np.float64).ravel()


def _rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(values))))


def measure_responses(adata: AnnData, config: MeasurementConfig | None = None) -> MeasurementTable:
    """Summarize eligible perturbation deltas against same-context controls.

    The response is a mean-expression delta on the input ``AnnData.X`` scale.
    No normalization or learned transformation is applied here; callers must
    record such preprocessing separately and provide the resulting AnnData.
    """

    config = config or MeasurementConfig()
    columns = config.columns
    missing = [columns.perturbation, columns.control, columns.assignment_class, config.context_column]
    missing = [name for name in missing if name not in adata.obs.columns]
    if missing:
        raise ValueError(f"AnnData.obs is missing required columns: {missing}")
    obs = adata.obs
    context = obs[config.context_column].astype(str).to_numpy()
    perturbations = obs[columns.perturbation].astype(str).to_numpy()
    controls = obs[columns.control].to_numpy(dtype=bool)
    eligible_class = (obs[columns.assignment_class] == columns.eligible_class).to_numpy()
    genes = tuple(map(str, adata.var_names))
    responses: list[PerturbationResponse] = []

    for ctx in sorted(set(context)):
        ctx_mask = context == ctx
        control_positions = np.flatnonzero(ctx_mask & controls)
        if len(control_positions):
            control_mean = _mean(adata.X, control_positions)
            control_noise = np.asarray(adata.X[control_positions].toarray() if hasattr(adata.X[control_positions], "toarray") else adata.X[control_positions], dtype=np.float64)
            control_noise = np.sqrt(np.mean(np.var(control_noise, axis=0)))
        else:
            control_mean = None
            control_noise = float("nan")
        for perturbation in sorted(set(perturbations[ctx_mask & eligible_class & ~controls])):
            positions = np.flatnonzero(ctx_mask & eligible_class & ~controls & (perturbations == perturbation))
            limitations: list[str] = []
            if control_mean is None:
                limitations.append("no same-context controls")
                delta = np.zeros(len(genes), dtype=np.float64)
            else:
                delta = _mean(adata.X, positions) - control_mean
            eligible = len(positions) >= config.min_cells and len(control_positions) >= config.min_controls
            if not eligible:
                limitations.append("below configured cell-count minimum")
            order = np.argsort(-np.abs(delta))[: config.top_k_genes]
            responses.append(
                PerturbationResponse(
                    perturbation=perturbation,
                    context=ctx,
                    cells=len(positions),
                    control_cells=len(control_positions),
                    response_signal=float(np.mean(np.abs(delta))),
                    noise_rms=float(control_noise) if np.isfinite(control_noise) else 0.0,
                    effect_magnitude=_rms(delta),
                    top_genes=tuple(genes[index] for index in order),
                    delta=tuple(map(float, delta)),
                    eligible=eligible,
                    limitations=tuple(limitations),
                )
            )

    config_dict = asdict(config)
    payload = {
        "dataset_fingerprint": dataset_fingerprint(adata),
        "config": config_dict,
        "genes": list(genes),
        "responses": [asdict(response) for response in responses],
    }
    artifact_sha256 = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    return MeasurementTable(payload["dataset_fingerprint"], config_dict, genes, tuple(responses), artifact_sha256)
