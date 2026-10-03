import anndata as ad
import numpy as np

from cellforge.reliability import SplitHalfClass, SplitHalfConfig, classify_anndata


def test_split_half_is_deterministic_and_detects_specific_response() -> None:
    rng = np.random.default_rng(4)
    control = rng.normal(0, 1, size=(80, 6))
    signal = control[:80].copy()
    signal[:, 0] += 4.0
    noise = rng.normal(0, 1, size=(80, 6))
    x = np.vstack([control, signal, noise])
    obs = {
        "target_gene": ["" for _ in range(80)] + ["A" for _ in range(80)] + ["B" for _ in range(80)],
        "is_control": [True] * 80 + [False] * 160,
        "context": ["ctx"] * 240,
    }
    data = ad.AnnData(x, obs=obs)
    config = SplitHalfConfig(min_cells=8, repeats=20, expressed_genes=6, seed=9)
    first = classify_anndata(data, config)
    second = classify_anndata(data, config)
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert first[0].classification in {SplitHalfClass.SPECIFIC, SplitHalfClass.SHARED}
    assert first[0].reliability >= 0.5


def test_split_half_marks_too_small_groups_insufficient() -> None:
    x = np.ones((10, 4))
    data = ad.AnnData(
        x,
        obs={
            "target_gene": [""] * 5 + ["A"] * 5,
            "is_control": [True] * 5 + [False] * 5,
            "context": ["ctx"] * 10,
        },
    )
    record = classify_anndata(data, SplitHalfConfig(min_cells=8, repeats=2))[0]
    assert record.classification is SplitHalfClass.INSUFFICIENT_DATA
