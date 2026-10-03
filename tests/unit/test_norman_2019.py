import anndata as ad
import numpy as np
import pandas as pd

from cellforge.datasets import inspect_norman, normalize_norman


def _raw() -> ad.AnnData:
    obs = pd.DataFrame(
        {
            "perturbation_name": ["ctrl", "CEBPE", "CEBPE+KLF1"],
            "perturbation_type": ["control", "single", "combination"],
        }
    )
    return ad.AnnData(np.ones((3, 2), dtype=np.float32), obs=obs, var=pd.DataFrame(index=["g0", "g1"]))


def test_norman_adapter_normalizes_control_and_combinations() -> None:
    data = normalize_norman(_raw())
    assert list(data.obs.target_genes) == ["", "CEBPE", "CEBPE+KLF1"]
    assert list(data.obs.assignment_class) == [
        "non_targeting_control",
        "single_target",
        "multi_target",
    ]
    report = inspect_norman(data)
    assert report.valid
    assert report.summary["combinations"] == 1
    assert report.summary["supported_ood_dimensions"] == ["unseen_perturbation"]


def test_norman_adapter_requires_perturbation_metadata() -> None:
    data = ad.AnnData(np.ones((2, 2), dtype=np.float32))
    try:
        normalize_norman(data)
    except ValueError as error:
        assert "perturbation" in str(error)
    else:  # pragma: no cover
        raise AssertionError("missing perturbation metadata was accepted")
