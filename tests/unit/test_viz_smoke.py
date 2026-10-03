import pytest

from cellforge.viz._optional import plotly
from cellforge.measure import PerturbationResponse
from cellforge.reliability import PerturbationReliability, ReliabilityClass
from cellforge.trust import ModelTrustRecord, ModelTrustStatus
from cellforge.viz import model_reality_check, perturbation_trust_map, response_explorer


def test_plotly_optional_loader_is_available_or_explicit():
    try:
        module = plotly()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert hasattr(module, "Figure")


def test_core_figures_consume_real_stage_records():
    response = PerturbationResponse("A", "ctx", 10, 10, 2.0, 1.0, 2.0, ("G1",), (2.0,), True)
    reliability = PerturbationReliability("A", "ctx", ReliabilityClass.SPECIFIC, 10, 10, 2.0, 2.0, 0.0, (), {})
    trust = ModelTrustRecord("A", "model", "split", 0.9, 0.1, 0.5, True, True, ReliabilityClass.SPECIFIC, ModelTrustStatus.TRUSTED, "ok")
    assert perturbation_trust_map((response,), (reliability,), {"A": trust}).data
    assert model_reality_check((trust,)).data
    assert response_explorer(response).data
