"""Rank candidates for human review without pretending to predict efficacy."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from cellforge.decision import Candidate
from cellforge.reliability import ReliabilityClass
from cellforge.trust import ModelTrustStatus


@dataclass(frozen=True)
class PriorityConfig:
    """Declared triage weights; the result is not a probability or efficacy score."""

    reliability_weight: float = 0.35
    response_weight: float = 0.25
    model_weight: float = 0.20
    evidence_weight: float = 0.20
    contradiction_penalty: float = 0.10
    missing_evidence_penalty: float = 0.05
    max_contradictions: int = 3

    def __post_init__(self) -> None:
        weights = (self.reliability_weight, self.response_weight, self.model_weight, self.evidence_weight)
        if any(weight < 0 for weight in weights) or not any(weights):
            raise ValueError("Priority weights must be non-negative and not all zero")
        if self.contradiction_penalty < 0 or self.missing_evidence_penalty < 0 or self.max_contradictions < 1:
            raise ValueError("Contradiction settings are invalid")


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    perturbation: str
    target: str
    context: str
    reliability: ReliabilityClass
    model_trust: ModelTrustStatus
    response_strength: float
    evidence_support: float
    contradiction_count: int = 0
    missing_evidence_count: int = 0
    evidence_ids: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    priority_score: float = field(init=False)

    def __post_init__(self) -> None:
        for name, value in (("response_strength", self.response_strength), ("evidence_support", self.evidence_support)):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if self.contradiction_count < 0 or self.missing_evidence_count < 0:
            raise ValueError("evidence counts cannot be negative")
        object.__setattr__(self, "priority_score", float("nan"))

    def score(self, config: PriorityConfig | None = None) -> float:
        config = config or PriorityConfig()
        reliability = {
            ReliabilityClass.SPECIFIC: 1.0,
            ReliabilityClass.SHARED: 0.5,
            ReliabilityClass.UNRELIABLE: 0.0,
            ReliabilityClass.INSUFFICIENT_DATA: 0.0,
        }[self.reliability]
        model = {
            ModelTrustStatus.TRUSTED: 1.0,
            ModelTrustStatus.LIMITED: 0.5,
            ModelTrustStatus.UNTRUSTED: 0.0,
            ModelTrustStatus.UNKNOWN: 0.0,
        }[self.model_trust]
        weight_total = config.reliability_weight + config.response_weight + config.model_weight + config.evidence_weight
        raw = (
            config.reliability_weight * reliability
            + config.response_weight * self.response_strength
            + config.model_weight * model
            + config.evidence_weight * self.evidence_support
        ) / weight_total
        penalty = config.contradiction_penalty * min(1.0, self.contradiction_count / config.max_contradictions)
        penalty += config.missing_evidence_penalty * min(1.0, float(self.missing_evidence_count) / config.max_contradictions)
        return max(0.0, min(1.0, raw - penalty))

    def to_candidate(self, config: PriorityConfig | None = None) -> Candidate:
        score = self.score(config)
        return Candidate(
            id=self.candidate_id,
            intervention=self.perturbation,
            target=self.target,
            evidence_ids=self.evidence_ids,
            rationale="Transparent triage components are preserved for human review.",
            limitations=self.limitations,
            measurement_reliability=self.reliability.value,
            model_trust=self.model_trust.value,
            priority_score=score,
            priority_components=(
                ("response_strength", self.response_strength),
                ("evidence_support", self.evidence_support),
                ("contradiction_count", float(self.contradiction_count)),
            ),
            contradiction_ids=self.contradiction_ids,
        )


def rank_candidates(
    evaluations: tuple[CandidateEvaluation, ...], config: PriorityConfig | None = None
) -> tuple[CandidateEvaluation, ...]:
    """Return a stable triage order; callers still must perform human review."""

    config = config or PriorityConfig()
    ids = [evaluation.candidate_id for evaluation in evaluations]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate IDs must be unique")
    return tuple(sorted(evaluations, key=lambda item: (-item.score(config), item.candidate_id)))
