import anndata as ad
import numpy as np
import pandas as pd

from cellforge.evaluation import EvaluationResult, PerturbationScore
from cellforge.measure import MeasurementConfig, measure_responses
from cellforge.reliability import ReliabilityClass, ReliabilityConfig, classify_table
from cellforge.trust import ModelTrustStatus, assess_model_trust


def _data() -> ad.AnnData:
    rows = [("control", True)] * 10 + [("A", False)] * 6 + [("B", False)] * 6 + [("C", False)] * 2
    obs = pd.DataFrame(rows, columns=["target_genes", "is_control"])
    obs["assignment_class"] = np.where(obs.is_control, "non_targeting_control", "single_target")
    obs["context"] = "ctx"
    x = np.zeros((len(obs), 3), dtype=np.float32)
    x[10:16, 0] = 5
    x[16:22, 0] = 5
    x[22:, 1] = 0.1
    return ad.AnnData(X=x, obs=obs, var=pd.DataFrame(index=["g0", "g1", "g2"]))


def test_measurement_preserves_explicit_config_and_marks_small_groups() -> None:
    table = measure_responses(_data(), MeasurementConfig(min_cells=5, min_controls=5, top_k_genes=2))
    by_name = {response.perturbation: response for response in table.responses}
    assert by_name["A"].eligible
    assert by_name["A"].top_genes[0] == "g0"
    assert not by_name["C"].eligible
    assert table.artifact_sha256 and len(table.artifact_sha256) == 64


def test_shared_and_insufficient_reliability_are_visible() -> None:
    table = measure_responses(_data(), MeasurementConfig(min_cells=5, min_controls=5))
    records = classify_table(table, ReliabilityConfig(min_cells=5, min_controls=5, max_shared_fraction=0.4))
    by_name = {record.perturbation: record for record in records}
    assert by_name["C"].classification is ReliabilityClass.INSUFFICIENT_DATA
    assert by_name["A"].classification is ReliabilityClass.SHARED


def _evaluation(model: str, values: dict[str, float]) -> EvaluationResult:
    return EvaluationResult(
        model,
        "fixture",
        "test",
        "split-1",
        tuple(PerturbationScore(name, 10, value, 1.0, True) for name, value in values.items()),
    )


def test_model_trust_cannot_be_trusted_when_linear_baseline_wins() -> None:
    records = assess_model_trust(
        _evaluation("advanced", {"A": 0.6, "B": 0.2}),
        _evaluation("control", {"A": 0.1, "B": 0.1}),
        _evaluation("linear", {"A": 0.7, "B": 0.1}),
        {"A": ReliabilityClass.SPECIFIC, "B": ReliabilityClass.SPECIFIC},
    )
    by_name = {record.perturbation: record for record in records}
    assert by_name["A"].trust_status is ModelTrustStatus.LIMITED
    assert by_name["B"].trust_status is ModelTrustStatus.TRUSTED


def test_undefined_control_baseline_is_noninformative_not_unknown() -> None:
    records = assess_model_trust(
        _evaluation("advanced", {"A": 0.6}),
        _evaluation("control", {"A": float("nan")}),
        _evaluation("linear", {"A": 0.2}),
        {"A": ReliabilityClass.SPECIFIC},
    )
    assert records[0].beats_control_baseline
    assert records[0].trust_status is ModelTrustStatus.TRUSTED
