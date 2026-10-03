import anndata as ad
import numpy as np
import pandas as pd
import pytest

from cellforge.splits import (
    SplitManifest,
    SplitSpec,
    apply_split,
    check_leakage,
    make_split,
)


def _adata(n_perts: int = 20, cells_per_pert: int = 30, n_controls: int = 120) -> ad.AnnData:
    rows = []
    for context in ("unstimulated_0h", "lps_3h"):
        for p in range(n_perts):
            rows += [(context, f"G{p:02d}", "single_target", False)] * cells_per_pert
        rows += [(context, "", "non_targeting_control", True)] * n_controls
        rows += [(context, "G00|G01", "multi_target", False)] * 5
        rows += [(context, "", "unassigned", False)] * 5
        rows += [(context, "TINY", "single_target", False)] * 3
    obs = pd.DataFrame(rows, columns=["context", "target_genes", "assignment_class", "is_control"])
    obs.index = pd.Index([f"cell_{i}" for i in range(len(obs))], name="cell_id")
    x = np.random.default_rng(0).poisson(1.0, size=(len(obs), 6)).astype(np.float32)
    return ad.AnnData(X=x, obs=obs, var=pd.DataFrame(index=[f"g{i}" for i in range(6)]))


def _pert_split(data: ad.AnnData, seed: int = 0) -> SplitManifest:
    return make_split(data, SplitSpec("unseen_perturbation", seed=seed))


def test_unseen_perturbation_split_is_leak_free() -> None:
    data = _adata()
    manifest = _pert_split(data)
    report = check_leakage(data, manifest)

    assert report.valid, report.issues
    declared = {name: set(perts) for name, perts in manifest.perturbations.items()}
    assert not declared["train"] & declared["test"]
    assert not declared["train"] & declared["val"]
    assert not declared["val"] & declared["test"]
    assert all(manifest.counts[name]["control_cells"] > 0 for name in ("train", "val", "test"))


def test_split_is_deterministic_and_seed_sensitive() -> None:
    data = _adata()
    assert _pert_split(data, 0).sha256 == _pert_split(data, 0).sha256
    assert _pert_split(data, 0).sha256 != _pert_split(data, 1).sha256


def test_ineligible_and_small_perturbations_are_excluded_and_counted() -> None:
    data = _adata()
    manifest = _pert_split(data)
    members = {cell for cells in manifest.partitions.values() for cell in cells}
    obs = data.obs

    assert not members & set(obs.index[obs.assignment_class == "multi_target"])
    assert not members & set(obs.index[obs.assignment_class == "unassigned"])
    assert not members & set(obs.index[obs.target_genes == "TINY"])
    assert manifest.excluded["perturbations_below_min_cells"] == 1
    assert manifest.excluded["ineligible_cells"] == 20


def test_manifest_round_trips_through_json() -> None:
    data = _adata()
    manifest = _pert_split(data)
    restored = SplitManifest.from_json(manifest.to_json())

    assert restored == manifest
    assert check_leakage(data, restored).valid


def test_leakage_check_catches_a_shared_perturbation() -> None:
    data = _adata()
    manifest = _pert_split(data)
    held_out = manifest.perturbations["test"][0]
    train_perts = manifest.perturbations["train"]
    tampered = SplitManifest(
        **{
            **manifest.__dict__,
            "perturbations": {**manifest.perturbations, "train": train_perts + (held_out,)},
        }
    )
    codes = {issue.code for issue in check_leakage(data, tampered).issues}
    assert {"perturbation_leakage", "manifest_hash_mismatch"} <= codes


def test_leakage_check_catches_a_cell_in_two_partitions() -> None:
    data = _adata()
    manifest = _pert_split(data)
    cell = manifest.partitions["test"][0]
    tampered = SplitManifest(
        **{
            **manifest.__dict__,
            "partitions": {**manifest.partitions, "train": manifest.partitions["train"] + (cell,)},
        }
    )
    assert "cell_overlap" in {issue.code for issue in check_leakage(data, tampered).issues}


def test_leakage_check_rejects_different_data() -> None:
    data = _adata()
    manifest = _pert_split(data)
    changed = data.copy()
    changed.X = changed.X + 1
    codes = {issue.code for issue in check_leakage(changed, manifest).issues}
    assert "dataset_mismatch" in codes


def test_context_split_trains_on_one_context_and_tests_on_another() -> None:
    data = _adata()
    spec = SplitSpec("unseen_context", train_context="unstimulated_0h", test_context="lps_3h")
    manifest = make_split(data, spec)

    assert check_leakage(data, manifest).valid
    contexts = data.obs.context
    assert set(contexts[list(manifest.partitions["train"])]) == {"unstimulated_0h"}
    assert set(contexts[list(manifest.partitions["val"])]) == {"unstimulated_0h"}
    assert set(contexts[list(manifest.partitions["test"])]) == {"lps_3h"}
    assert any("within the training context" in note for note in manifest.notes)


def test_apply_split_returns_only_that_partition() -> None:
    data = _adata()
    manifest = _pert_split(data)
    test = apply_split(data, manifest, "test")
    assert set(test.obs_names) == set(manifest.partitions["test"])
    with pytest.raises(ValueError):
        apply_split(data, manifest, "holdout")


def test_invalid_inputs_fail_loudly() -> None:
    data = _adata()
    with pytest.raises(ValueError, match="Unsupported split kind"):
        SplitSpec("random")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires train_context"):
        SplitSpec("unseen_context")
    with pytest.raises(ValueError, match="missing required columns"):
        broken = ad.AnnData(X=data.X, obs=data.obs.drop(columns="is_control"))
        make_split(broken, SplitSpec("unseen_perturbation"))
    with pytest.raises(ValueError, match="at least 3 perturbations"):
        make_split(_adata(n_perts=2), SplitSpec("unseen_perturbation"))
