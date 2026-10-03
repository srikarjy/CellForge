import numpy as np
import pandas as pd
from anndata import AnnData

from cellforge.evaluation import EvaluationResult, PerturbationScore
from cellforge.evidence import EvidenceDirection, EvidenceType, normalize_evidence
from cellforge.workflow import run_norman_decision
from cellforge.measure import MeasurementConfig
from cellforge.reliability import ReliabilityConfig
from cellforge.splits import SplitColumns


def _norman_subset() -> AnnData:
    # A deterministic, tiny Norman-shaped fixture: controls plus three guide assignments.
    rows = []
    values = []
    for i in range(6):
        rows.append((f"ctrl_{i}", "control", True, "control", "cell"))
        values.append([1.0, 1.0, 1.0, 1.0])
    for name, effect in (("A", [3.0, 1.0, 1.0, 1.0]), ("B", [1.0, 3.0, 1.0, 1.0]), ("C", [1.0, 1.0, 3.0, 1.0])):
        for i in range(6):
            rows.append((f"{name}_{i}", name, False, "single_target", "cell"))
            values.append(effect)
    obs = pd.DataFrame(rows, columns=["cell", "perturbation", "is_control", "assignment_class", "context"]).set_index("cell")
    var = pd.DataFrame(index=["G1", "G2", "G3", "G4"])
    return AnnData(np.asarray(values, dtype=float), obs=obs, var=var)


def _evaluation(model: str, scores: dict[str, float]) -> EvaluationResult:
    return EvaluationResult(
        model=model,
        information_access="fixture",
        partition="unseen_perturbation",
        split_sha256="split-fixture",
        scores=tuple(PerturbationScore(name, 6, value, 0.1, True) for name, value in sorted(scores.items())),
    )


def test_norman_subset_runs_to_one_deterministic_decision_package():
    evidence = (
        normalize_evidence(
            source="Reactome",
            source_id="reactome:A",
            target="A",
            claim="A participates in a fixture pathway",
            evidence_type=EvidenceType.PATHWAY,
            direction=EvidenceDirection.SUPPORTS,
            payload={"pathway": "fixture"},
        ),
        normalize_evidence(
            source="DepMap",
            source_id="depmap:A",
            target="A",
            claim="A has a dependency warning",
            evidence_type=EvidenceType.DEPENDENCY,
            direction=EvidenceDirection.CONTRADICTS,
            payload={"dependency": "warning"},
        ),
    )
    kwargs = {
        "advanced": _evaluation("advanced", {"A": 0.9, "B": 0.6, "C": 0.2}),
        "control": _evaluation("control", {"A": 0.1, "B": 0.1, "C": 0.1}),
        "linear": _evaluation("linear", {"A": 0.5, "B": 0.8, "C": 0.3}),
        "evidence": evidence,
        "run_id": "norman-fixture",
        "measurement_config": MeasurementConfig(
            columns=SplitColumns(perturbation="perturbation"), min_cells=1, min_controls=1
        ),
        "reliability_config": ReliabilityConfig(min_cells=1, min_controls=1),
    }
    first = run_norman_decision(_norman_subset(), **kwargs)
    second = run_norman_decision(_norman_subset(), **kwargs)
    assert first.measurement.responses
    assert len(first.reliability) == len(first.model_trust) == 3
    assert first.contradictions and first.contradictions[0].candidate == "A"
    assert first.package.status.value == "needs_review"
    assert first.package.sha256 == second.package.sha256
    assert first.package.candidates[0].measurement_summary
    assert first.package.candidates[0].model_summaries
    assert first.package.provenance[-1][0] == "workflow_manifest_sha256"
    assert any(candidate.contradiction_ids for candidate in first.package.candidates)
