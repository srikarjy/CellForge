"""Model trust is a bounded comparison against baselines, not a probability."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

import numpy as np

from cellforge.evaluation import EvaluationResult
from cellforge.reliability import ReliabilityClass


class ModelTrustStatus(str, Enum):
    TRUSTED = "TRUSTED"
    LIMITED = "LIMITED"
    UNTRUSTED = "UNTRUSTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ModelTrustRecord:
    perturbation: str
    model: str
    evaluation_setting: str
    advanced_score: float
    control_score: float
    linear_score: float
    beats_control_baseline: bool
    beats_linear_baseline: bool
    measurement_reliability: ReliabilityClass
    trust_status: ModelTrustStatus
    reason: str


def _scores(result: EvaluationResult) -> dict[str, float]:
    return {score.perturbation: score.pearson_delta for score in result.scores}


def assess_model_trust(
    advanced: EvaluationResult,
    control: EvaluationResult,
    linear: EvaluationResult,
    reliability: Mapping[str, ReliabilityClass],
    *,
    margin: float = 0.0,
) -> tuple[ModelTrustRecord, ...]:
    """Compare each advanced prediction with both baselines for matched perturbations."""

    if margin < 0:
        raise ValueError("margin cannot be negative")
    advanced_scores, control_scores, linear_scores = _scores(advanced), _scores(control), _scores(linear)
    names = tuple(sorted(set(advanced_scores) & set(control_scores) & set(linear_scores)))
    records = []
    for name in names:
        advanced_score, control_score, linear_score = (
            advanced_scores[name], control_scores[name], linear_scores[name]
        )
        rel = reliability.get(name, ReliabilityClass.INSUFFICIENT_DATA)
        finite = all(np.isfinite(value) for value in (advanced_score, control_score, linear_score))
        beats_control = bool(finite and advanced_score > control_score + margin)
        beats_linear = bool(finite and advanced_score > linear_score + margin)
        if not finite:
            status, reason = ModelTrustStatus.UNKNOWN, "At least one matched metric is undefined."
        elif not beats_control:
            status, reason = ModelTrustStatus.UNTRUSTED, "Advanced model does not beat the no-change baseline."
        elif rel is not ReliabilityClass.SPECIFIC:
            status, reason = ModelTrustStatus.LIMITED, f"Measurement reliability is {rel.value}."
        elif not beats_linear:
            status, reason = ModelTrustStatus.LIMITED, "Model beats no-change baseline but not the linear baseline."
        else:
            status, reason = ModelTrustStatus.TRUSTED, "Model beats both declared baselines on this matched perturbation."
        records.append(
            ModelTrustRecord(
                name,
                advanced.model,
                advanced.partition,
                advanced_score,
                control_score,
                linear_score,
                beats_control,
                beats_linear,
                rel,
                status,
                reason,
            )
        )
    return tuple(records)
