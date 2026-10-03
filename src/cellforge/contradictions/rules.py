"""Conservative contradiction rules; findings are surfaced, never auto-resolved."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cellforge.evidence import EvidenceDirection, EvidenceRecord
from cellforge.measure import PerturbationResponse
from cellforge.reliability import ReliabilityClass
from cellforge.trust import ModelTrustRecord


class ContradictionSeverity(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


@dataclass(frozen=True)
class Contradiction:
    candidate: str
    source_a: str
    source_b: str
    type: str
    severity: ContradictionSeverity
    explanation: str
    references: tuple[str, ...]


def find_evidence_contradictions(records: tuple[EvidenceRecord, ...]) -> tuple[Contradiction, ...]:
    """Find same-target support/contradict pairs with deterministic ordering."""

    findings: list[Contradiction] = []
    for index, left in enumerate(records):
        if left.direction is EvidenceDirection.UNKNOWN:
            continue
        for right in records[index + 1 :]:
            if right.target != left.target or right.direction is EvidenceDirection.UNKNOWN:
                continue
            opposite = {left.direction, right.direction} == {
                EvidenceDirection.SUPPORTS,
                EvidenceDirection.CONTRADICTS,
            }
            if opposite:
                findings.append(
                    Contradiction(
                        candidate=left.target,
                        source_a=left.source,
                        source_b=right.source,
                        type="external_evidence_direction",
                        severity=ContradictionSeverity.MAJOR,
                        explanation="Independent evidence records assign opposite directions to the same target.",
                        references=(left.source_id, right.source_id),
                    )
                )
    return tuple(findings)


def find_model_contradictions(
    records: tuple[ModelTrustRecord, ...],
    responses: tuple[PerturbationResponse, ...] = (),
    *,
    strong_response: float = 0.5,
    weak_model: float = 0.25,
) -> tuple[Contradiction, ...]:
    """Surface model-vs-baseline and model-vs-measurement conflicts."""
    response_by_name = {item.perturbation: item for item in responses}
    findings: list[Contradiction] = []
    for record in records:
        if record.beats_control_baseline and not record.beats_linear_baseline:
            findings.append(
                Contradiction(
                    record.perturbation,
                    record.model,
                    "linear_baseline",
                    "model_vs_baseline",
                    ContradictionSeverity.MAJOR,
                    "Advanced model does not beat the declared linear baseline.",
                    (record.model, record.evaluation_setting),
                )
            )
        response = response_by_name.get(record.perturbation)
        if response and response.effect_magnitude >= strong_response and record.advanced_score <= weak_model:
            findings.append(
                Contradiction(
                    record.perturbation,
                    "measurement",
                    record.model,
                    "measurement_vs_model",
                    ContradictionSeverity.MAJOR,
                    "Measured response is strong while the advanced model predicts weak agreement.",
                    (record.model, record.evaluation_setting),
                )
            )
        if record.measurement_reliability is not ReliabilityClass.SPECIFIC and record.advanced_score >= strong_response:
            findings.append(
                Contradiction(
                    record.perturbation,
                    "measurement_reliability",
                    record.model,
                    "reliability_vs_model",
                    ContradictionSeverity.MINOR,
                    f"Model score is strong but measurement reliability is {record.measurement_reliability.value}.",
                    (record.model, record.evaluation_setting),
                )
            )
    return tuple(findings)
