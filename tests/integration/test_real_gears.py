import pytest


@pytest.mark.model_integration
def test_real_gears_environment_is_explicitly_optional():
    pytest.importorskip("gears")
