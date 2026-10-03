from cellforge.prioritize import CandidateEvaluation, PriorityConfig, rank_candidates
from cellforge.reliability import ReliabilityClass
from cellforge.trust import ModelTrustStatus


def _candidate(candidate_id: str, reliability: ReliabilityClass, trust: ModelTrustStatus) -> CandidateEvaluation:
    return CandidateEvaluation(candidate_id, candidate_id, candidate_id, "ctx", reliability, trust, 1.0, 1.0)


def test_unreliable_measurement_cannot_win_on_model_signal_alone() -> None:
    reliable = _candidate("reliable", ReliabilityClass.SPECIFIC, ModelTrustStatus.LIMITED)
    noisy = _candidate("noisy", ReliabilityClass.UNRELIABLE, ModelTrustStatus.TRUSTED)
    ranked = rank_candidates((noisy, reliable))
    assert [candidate.candidate_id for candidate in ranked] == ["reliable", "noisy"]
    assert ranked[0].to_candidate().measurement_reliability == "SPECIFIC"
    assert ranked[0].to_candidate().priority_components


def test_ranking_is_stable_and_duplicate_ids_fail() -> None:
    config = PriorityConfig(contradiction_penalty=0.2)
    first = _candidate("a", ReliabilityClass.SPECIFIC, ModelTrustStatus.TRUSTED)
    second = _candidate("b", ReliabilityClass.SPECIFIC, ModelTrustStatus.TRUSTED)
    assert [item.candidate_id for item in rank_candidates((second, first), config)] == ["a", "b"]
    try:
        rank_candidates((first, first))
    except ValueError as error:
        assert "unique" in str(error)
    else:  # pragma: no cover
        raise AssertionError("duplicate candidate IDs were accepted")


def test_untrusted_model_cannot_dominate_and_missing_evidence_is_explicit() -> None:
    candidate = CandidateEvaluation(
        "candidate",
        "candidate",
        "candidate",
        "ctx",
        ReliabilityClass.SPECIFIC,
        ModelTrustStatus.UNTRUSTED,
        1.0,
        0.0,
        missing_evidence_count=2,
        limitations=("advanced model lost to baseline",),
    )
    package_candidate = candidate.to_candidate()
    assert package_candidate.model_trust == "UNTRUSTED"
    assert package_candidate.priority_score < 0.8
    assert "advanced model lost to baseline" in package_candidate.limitations
    assert candidate.missing_evidence_count == 2


def test_contradictions_are_visible_and_ranking_does_not_change_review_state() -> None:
    candidate = CandidateEvaluation(
        "candidate",
        "candidate",
        "candidate",
        "ctx",
        ReliabilityClass.SPECIFIC,
        ModelTrustStatus.TRUSTED,
        1.0,
        1.0,
        contradiction_count=1,
        contradiction_ids=("evidence-conflict",),
    )
    result = candidate.to_candidate()
    assert result.contradiction_ids == ("evidence-conflict",)
    assert result.priority_score < 1.0
