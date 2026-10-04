"""Configurable, provenance-preserving measurement reliability decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import numpy as np

from cellforge.measure import MeasurementTable, PerturbationResponse


class ReliabilityClass(str, Enum):
    SPECIFIC = "SPECIFIC"
    SHARED = "SHARED"
    UNRELIABLE = "UNRELIABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class ReliabilityConfig:
    """Thresholds are explicit and part of the output provenance."""

    min_cells: int = 20
    min_controls: int = 20
    min_signal_to_noise: float = 1.5
    shared_similarity: float = 0.8
    max_shared_fraction: float = 0.8
    method: str = "similarity_and_signal_v1"

    def __post_init__(self) -> None:
        if self.min_cells < 1 or self.min_controls < 1:
            raise ValueError("minimum cell counts must be positive")
        if self.min_signal_to_noise < 0 or not 0 <= self.shared_similarity <= 1:
            raise ValueError("reliability thresholds are invalid")
        if not 0 <= self.max_shared_fraction <= 1:
            raise ValueError("max_shared_fraction must be in [0, 1]")


@dataclass(frozen=True)
class PerturbationReliability:
    perturbation: str
    context: str
    classification: ReliabilityClass
    cells: int
    control_cells: int
    response_signal: float
    signal_to_noise: float
    shared_response_fraction: float | None
    limitations: tuple[str, ...]
    config: dict[str, Any]
    method: str = "legacy_similarity_signal_v1"
    reliability_statistic: float | None = None
    median_split_correlation: float | None = None
    shared_cosine: float | None = None
    shared_variance_fraction: float | None = None
    legacy_signal: float | None = None
    legacy_noise: float | None = None
    legacy_snr: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        return payload

    @property
    def reliability(self) -> float | None:
        """Method-neutral alias used by split-half diagnostics."""
        return self.reliability_statistic

    @property
    def response_magnitude(self) -> float:
        return self.response_signal


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    left_norm, right_norm = np.linalg.norm(left), np.linalg.norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def classify_reliability(
    response: PerturbationResponse,
    peers: tuple[PerturbationResponse, ...] = (),
    config: ReliabilityConfig | None = None,
) -> PerturbationReliability:
    """Assign a documented class; this is not a probability of correctness."""

    config = config or ReliabilityConfig()
    limitations = list(response.limitations)
    if response.cells < config.min_cells or response.control_cells < config.min_controls:
        classification = ReliabilityClass.INSUFFICIENT_DATA
        limitations.append("insufficient cells or controls for configured reliability rule")
        shared_fraction = None
    else:
        similarities = [
            _cosine(np.asarray(response.delta), np.asarray(peer.delta))
            for peer in peers
            if peer.perturbation != response.perturbation and peer.context == response.context and peer.eligible
        ]
        shared_fraction = (
            float(np.mean(np.asarray(similarities) >= config.shared_similarity)) if similarities else 0.0
        )
        if response.signal_to_noise < config.min_signal_to_noise:
            classification = ReliabilityClass.UNRELIABLE
            limitations.append("response signal is below configured signal-to-noise threshold")
        elif shared_fraction > config.max_shared_fraction:
            classification = ReliabilityClass.SHARED
            limitations.append("response is highly similar to other perturbation responses")
        else:
            classification = ReliabilityClass.SPECIFIC
    return PerturbationReliability(
        response.perturbation,
        response.context,
        classification,
        response.cells,
        response.control_cells,
        response.response_signal,
        response.signal_to_noise,
        shared_fraction,
        tuple(dict.fromkeys(limitations)),
        asdict(config),
        method=config.method,
        reliability_statistic=response.signal_to_noise,
        legacy_signal=response.response_signal,
        legacy_noise=response.noise_rms,
        legacy_snr=response.signal_to_noise,
    )


def classify_table(table: MeasurementTable, config: ReliabilityConfig | None = None) -> tuple[PerturbationReliability, ...]:
    config = config or ReliabilityConfig()
    records = tuple(classify_reliability(response, table.responses, config) for response in table.responses)
    payload = json.dumps([asdict(record) for record in records], sort_keys=True, default=str, separators=(",", ":"))
    # Force evaluation of the deterministic artifact identity during construction/use.
    hashlib.sha256(payload.encode()).hexdigest()
    return records
