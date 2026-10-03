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
    training_mean_score: float = float("nan")
    beats_training_mean: bool = False


def _scores(result: EvaluationResult) -> dict[str, float]:
    return {score.perturbation: score.pearson_delta for score in result.scores}


def assess_model_trust(
    advanced: EvaluationResult,
    control: EvaluationResult,
    linear: EvaluationResult,
    reliability: Mapping[str, ReliabilityClass],
    *,
    margin: float = 0.0,
    training_mean: EvaluationResult | None = None,
) -> tuple[ModelTrustRecord, ...]:
    """Compare each advanced prediction with both baselines for matched perturbations."""

    if margin < 0:
        raise ValueError("margin cannot be negative")
    advanced_scores, control_scores, linear_scores = _scores(advanced), _scores(control), _scores(linear)
    training_scores = _scores(training_mean) if training_mean is not None else {}
    names = tuple(sorted(set(advanced_scores) & set(control_scores) & set(linear_scores)))
    records = []
    for name in names:
        advanced_score, control_score, linear_score = (
            advanced_scores[name], control_scores[name], linear_scores[name]
        )
        rel = reliability.get(name, ReliabilityClass.INSUFFICIENT_DATA)
        training_score = training_scores.get(name, float("nan"))
        finite_advanced = np.isfinite(advanced_score)
        finite_control = np.isfinite(control_score)
        finite_linear = np.isfinite(linear_score)
        finite_training = np.isfinite(training_score)
        beats_control = bool(finite_advanced and (not finite_control or advanced_score > control_score + margin))
        beats_linear = bool(finite_advanced and finite_linear and advanced_score > linear_score + margin)
        beats_training = bool(finite_advanced and (training_mean is None or not finite_training or advanced_score > training_score + margin))
        if not finite_advanced or not finite_linear:
            status, reason = ModelTrustStatus.UNKNOWN, "At least one matched metric is undefined."
        elif not beats_control:
            status, reason = ModelTrustStatus.UNTRUSTED, "Advanced model does not beat the no-change baseline."
        elif rel is not ReliabilityClass.SPECIFIC:
            status, reason = ModelTrustStatus.LIMITED, f"Measurement reliability is {rel.value}."
        elif not beats_linear:
            status, reason = ModelTrustStatus.LIMITED, "Model beats no-change baseline but not the linear baseline."
        elif training_mean is not None and not beats_training:
            status, reason = ModelTrustStatus.LIMITED, "Model beats no-change and linear baselines but not the training-mean baseline."
        else:
            status, reason = ModelTrustStatus.TRUSTED, "Model beats all declared baselines on this matched perturbation."
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
                training_score,
                beats_training,
            )
        )
    return tuple(records)
