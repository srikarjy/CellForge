"""Stable output contract for CellForge's evidence-to-experiment workflow."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any


class EvidenceType(str, Enum):
    LITERATURE = "literature"
    DATASET = "dataset"
    DATABASE = "database"
    MODEL = "model"
    STRUCTURE = "structure"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Evidence:
    id: str
    type: EvidenceType
    source: str
    source_id: str
    claim: str
    artifact_sha256: str | None = None
    url: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class PredictionSummary:
    model: str
    split: str
    metric: str
    value: float
    eligible_count: int
    manifest_sha256: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.value):
            raise ValueError("Prediction metric value must be finite")
        if self.eligible_count < 0:
            raise ValueError("eligible_count cannot be negative")


@dataclass(frozen=True)
class Candidate:
    id: str
    intervention: str
    target: str
    evidence_ids: tuple[str, ...] = ()
    predictions: tuple[PredictionSummary, ...] = ()
    rationale: str = ""
    limitations: tuple[str, ...] = ()
    measurement_reliability: str | None = None
    model_trust: str | None = None
    priority_score: float | None = None
    priority_components: tuple[tuple[str, float], ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    measurement_summary: tuple[tuple[str, str], ...] = ()
    model_summaries: tuple[PredictionSummary, ...] = ()


@dataclass(frozen=True)
class DecisionPackage:
    run_id: str
    question: str
    scope: str
    workflow_manifest_sha256: str
    evidence: tuple[Evidence, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    status: PackageStatus = PackageStatus.DRAFT
    reviewer: str | None = None
    review_notes: str = ""
    provenance: tuple[tuple[str, str], ...] = ()
    _sha256: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        for field_name in ("run_id", "question", "scope", "workflow_manifest_sha256"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        evidence_ids = [item.id for item in self.evidence]
        candidate_ids = [item.id for item in self.candidates]
        if any(not item.strip() for item in evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be non-empty and unique")
        if any(not item.strip() for item in candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate IDs must be non-empty and unique")
        known = set(evidence_ids)
        for candidate in self.candidates:
            missing = set(candidate.evidence_ids) - known
            if missing:
                raise ValueError(f"Candidate {candidate.id!r} references unknown evidence: {sorted(missing)}")
        if self.status is PackageStatus.APPROVED and not (self.reviewer or "").strip():
            raise ValueError("Approved packages require a reviewer")

    def approve(self, reviewer: str, notes: str = "") -> DecisionPackage:
        if not reviewer.strip():
            raise ValueError("Reviewer is required")
        return replace(self, status=PackageStatus.APPROVED, reviewer=reviewer.strip(), review_notes=notes)

    def request_review(self) -> DecisionPackage:
        return replace(self, status=PackageStatus.NEEDS_REVIEW)

    def reject(self, reviewer: str, notes: str) -> DecisionPackage:
        if not reviewer.strip() or not notes.strip():
            raise ValueError("Rejected packages require a reviewer and notes")
        return replace(self, status=PackageStatus.REJECTED, reviewer=reviewer.strip(), review_notes=notes)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("_sha256", None)
        return value

    @property
    def sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_json(self) -> str:
        return json.dumps({**self.to_dict(), "package_sha256": self.sha256}, sort_keys=True, indent=2) + "\n"
