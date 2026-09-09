from pathlib import Path

import pytest

from cellforge.datasets import inspect_dixit_bmdc


SOURCE = Path("data/raw/dixit_2016_bmdc")


@pytest.mark.skipif(not SOURCE.exists(), reason="Public dataset payload is not checked into Git")
def test_downloaded_source_passes_structural_validation() -> None:
    report = inspect_dixit_bmdc(SOURCE)

    assert report.valid, report.to_dict()
    conditions = report.summary["conditions"]
    assert conditions["shared_target_genes"] == 24
    assert conditions["shared_expression_genes"] == 16_564
