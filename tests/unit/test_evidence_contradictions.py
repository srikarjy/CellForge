from cellforge.contradictions import ContradictionSeverity, find_evidence_contradictions, find_model_contradictions
from cellforge.evidence import EvidenceDirection, EvidenceType, normalize_evidence
from cellforge.measure import PerturbationResponse
from cellforge.reliability import ReliabilityClass
from cellforge.trust import ModelTrustRecord, ModelTrustStatus


def test_evidence_is_hashed_and_contradictions_are_explicit() -> None:
    support = normalize_evidence(
        source="reactome",
        source_id="R-HSA-1",
        target="GeneA",
        claim="GeneA participates in pathway P.",
        evidence_type=EvidenceType.PATHWAY,
        direction=EvidenceDirection.SUPPORTS,
        payload={"pathway": "P", "target": "GeneA"},
    )
    contradict = normalize_evidence(
        source="pubmed",
        source_id="PMID:2",
        target="GeneA",
        claim="A study reports no effect.",
        evidence_type=EvidenceType.LITERATURE,
        direction=EvidenceDirection.CONTRADICTS,
        payload={"pmid": 2, "effect": "none"},
    )
    findings = find_evidence_contradictions((support, contradict))
    assert len(support.payload_hash) == 64
    assert findings[0].severity is ContradictionSeverity.MAJOR
    assert findings[0].references == ("R-HSA-1", "PMID:2")


def test_model_baseline_and_reliability_conflicts_are_explicit() -> None:
    record = ModelTrustRecord("A", "GEARS", "split", 0.8, 0.1, 0.9, True, False, ReliabilityClass.SHARED, ModelTrustStatus.LIMITED, "linear wins")
    response = PerturbationResponse("A", "ctx", 20, 20, 1.0, 1.0, 1.0, ("G1",), (1.0,), True)
    findings = find_model_contradictions((record,), (response,))
    assert {finding.type for finding in findings} == {"model_vs_baseline", "reliability_vs_model"}
