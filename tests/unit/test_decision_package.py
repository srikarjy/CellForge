import pytest

from cellforge.decision import Candidate, DecisionPackage, Evidence, EvidenceType, PackageStatus, PredictionSummary


def _package() -> DecisionPackage:
    evidence = Evidence("lit-1", EvidenceType.LITERATURE, "pubmed", "PMID:123", "Target is expressed.")
    candidate = Candidate(
        "cand-1", "guide-1", "GeneA", ("lit-1",),
        (PredictionSummary("baseline", "unseen_perturbation", "pearson", 0.4, 12, "split"),),
        "Evidence-backed candidate.",
    )
    return DecisionPackage("run-1", "Which perturbation should we test?", "immune cells", "workflow", (evidence,), (candidate,))


def test_package_is_traceable_and_review_is_explicit() -> None:
    package = _package()
    assert package.status is PackageStatus.DRAFT
    assert len(package.sha256) == 64
    reviewed = package.request_review().approve("Ada", "Checked limitations.")
    assert reviewed.status is PackageStatus.APPROVED
    assert reviewed.sha256 != package.sha256
    assert '"package_sha256"' in reviewed.to_json()


def test_unknown_evidence_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown evidence"):
        DecisionPackage("run-1", "question", "scope", "workflow", candidates=(Candidate("c", "i", "t", ("missing",)),))


def test_approval_requires_reviewer() -> None:
    with pytest.raises(ValueError, match="Reviewer"):
        _package().approve(" ")
