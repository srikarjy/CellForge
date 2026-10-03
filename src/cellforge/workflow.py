"""Small, deterministic orchestration for the CellForge MVP decision flow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from cellforge.contradictions import Contradiction, find_evidence_contradictions, find_model_contradictions
from cellforge.decision import DecisionPackage, Evidence, EvidenceType, PackageStatus, PredictionSummary
from cellforge.evidence import EvidenceRecord, EvidenceType as ExternalEvidenceType
from cellforge.evaluation import EvaluationResult
from cellforge.measure import MeasurementConfig, MeasurementTable, measure_responses
from cellforge.prioritize import CandidateEvaluation, PriorityConfig, rank_candidates
from cellforge.reliability import (
    PerturbationReliability,
    ReliabilityClass,
    ReliabilityConfig,
    classify_table,
)
from cellforge.trust import ModelTrustRecord, assess_model_trust


@dataclass(frozen=True)
class NormanDecisionRun:
    """All stage outputs for one reproducible run, ending in its package."""

    run_id: str
    measurement: MeasurementTable
    reliability: tuple[PerturbationReliability, ...]
    model_trust: tuple[ModelTrustRecord, ...]
    evidence: tuple[EvidenceRecord, ...]
    contradictions: tuple[Contradiction, ...]
    ranked: tuple[CandidateEvaluation, ...]
    package: DecisionPackage


def _decision_evidence(record: EvidenceRecord) -> Evidence:
    kind = {
        ExternalEvidenceType.LITERATURE: EvidenceType.LITERATURE,
        ExternalEvidenceType.DATASET: EvidenceType.DATASET,
        ExternalEvidenceType.PATHWAY: EvidenceType.DATABASE,
        ExternalEvidenceType.DEPENDENCY: EvidenceType.DATABASE,
        ExternalEvidenceType.STRUCTURE: EvidenceType.STRUCTURE,
    }[record.evidence_type]
    return Evidence(
        id=record.source_id,
        type=kind,
        source=record.source,
        source_id=record.source_id,
        claim=record.claim,
        artifact_sha256=record.payload_hash,
        url=record.url,
        limitations=record.limitations,
    )


def run_norman_decision(
    adata,
    *,
    advanced: EvaluationResult,
    control: EvaluationResult,
    linear: EvaluationResult,
    evidence: tuple[EvidenceRecord, ...] = (),
    run_id: str = "norman-mvp",
    measurement_config: MeasurementConfig | None = None,
    reliability_config: ReliabilityConfig | None = None,
    priority_config: PriorityConfig | None = None,
) -> NormanDecisionRun:
    """Run every MVP stage without network access or hidden mutable state."""

    measurement = measure_responses(adata, measurement_config)
    reliability = classify_table(measurement, reliability_config)
    reliability_by_perturbation = {record.perturbation: record.classification for record in reliability}
    trust = assess_model_trust(advanced, control, linear, reliability_by_perturbation)
    trust_by_perturbation = {record.perturbation: record for record in trust}
    contradictions = find_evidence_contradictions(tuple(evidence)) + find_model_contradictions(trust, measurement.responses)
    evidence_by_target: dict[str, list[EvidenceRecord]] = {}
    for record in evidence:
        evidence_by_target.setdefault(record.target, []).append(record)
    contradiction_by_target: dict[str, list[Contradiction]] = {}
    for finding in contradictions:
        contradiction_by_target.setdefault(finding.candidate, []).append(finding)
    response_by_perturbation = {response.perturbation: response for response in measurement.responses}

    evaluations: list[CandidateEvaluation] = []
    for perturbation in sorted(set(response_by_perturbation) & set(trust_by_perturbation)):
        response = response_by_perturbation[perturbation]
        trust_record = trust_by_perturbation[perturbation]
        target_records = tuple(evidence_by_target.get(perturbation, ()))
        supports = sum(record.direction.value == "supports" for record in target_records)
        support = supports / len(target_records) if target_records else 0.0
        findings = tuple(contradiction_by_target.get(perturbation, ()))
        limitations = tuple(dict.fromkeys(response.limitations + (trust_record.reason,)))
        evaluations.append(
            CandidateEvaluation(
                candidate_id=f"{run_id}:{perturbation}",
                perturbation=perturbation,
                target=perturbation,
                context=response.context,
                reliability=reliability_by_perturbation.get(perturbation, ReliabilityClass.INSUFFICIENT_DATA),
                model_trust=trust_record.trust_status,
                response_strength=min(1.0, response.effect_magnitude),
                evidence_support=support,
                contradiction_count=len(findings),
                missing_evidence_count=0 if target_records else 1,
                evidence_ids=tuple(record.source_id for record in target_records),
                contradiction_ids=tuple(f"{finding.candidate}:{index}" for index, finding in enumerate(findings)),
                limitations=limitations,
            )
        )
    ranked = rank_candidates(tuple(evaluations), priority_config)
    package_evidence = tuple(_decision_evidence(record) for record in evidence)
    package_candidates = []
    for evaluation in ranked:
        candidate = evaluation.to_candidate(priority_config)
        trust_record = trust_by_perturbation[evaluation.perturbation]
        response = response_by_perturbation[evaluation.perturbation]
        candidate = candidate.__class__(
            **{
                **candidate.__dict__,
                "measurement_summary": (
                    ("cells", str(response.cells)),
                    ("control_cells", str(response.control_cells)),
                    ("effect_magnitude", f"{response.effect_magnitude:.8g}"),
                    ("artifact_sha256", measurement.artifact_sha256),
                ),
                "model_summaries": (
                    PredictionSummary(
                        model=trust_record.model,
                        split=trust_record.evaluation_setting,
                        metric="pearson_delta",
                        value=trust_record.advanced_score,
                        eligible_count=1,
                        manifest_sha256=advanced.split_sha256,
                    ),
                ),
            }
        )
        package_candidates.append(candidate)
    manifest_payload = {
        "run_id": run_id,
        "dataset_fingerprint": measurement.dataset_fingerprint,
        "measurement_artifact": measurement.artifact_sha256,
        "model_manifests": sorted({advanced.split_sha256, control.split_sha256, linear.split_sha256}),
        "advanced_model_metadata": advanced.model_metadata,
        "evidence_payloads": sorted(record.payload_hash for record in evidence),
        "reliability_config": reliability_config.__dict__ if reliability_config else ReliabilityConfig().__dict__,
    }
    manifest_hash = hashlib.sha256(json.dumps(manifest_payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    package = DecisionPackage(
        run_id=run_id,
        question="Which perturbations deserve further scientific review, and why?",
        scope="Norman 2019 Perturb-seq subset",
        workflow_manifest_sha256=manifest_hash,
        evidence=package_evidence,
        candidates=tuple(package_candidates),
        status=PackageStatus.NEEDS_REVIEW if package_candidates else PackageStatus.DRAFT,
        provenance=(
            ("dataset_fingerprint", measurement.dataset_fingerprint),
            ("measurement_artifact_sha256", measurement.artifact_sha256),
            ("advanced_model", advanced.model),
            ("split_sha256", advanced.split_sha256),
            ("advanced_model_config_sha256", str(advanced.model_metadata.get("model_config_sha256", ""))),
            ("workflow_manifest_sha256", manifest_hash),
        ),
    )
    return NormanDecisionRun(run_id, measurement, reliability, trust, tuple(evidence), contradictions, ranked, package)
