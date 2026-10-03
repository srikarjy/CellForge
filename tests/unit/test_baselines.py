import anndata as ad
import numpy as np
import pandas as pd
import pytest

from cellforge.baselines import (
    ControlMean,
    EmbeddingKNN,
    EmbeddingRidge,
    SeenPerturbationDelta,
    TrainMeanShift,
)
from cellforge.evaluation import (
    Predictions,
    delta_mse,
    delta_pearson,
    evaluate_model,
    pseudobulk,
    select_by_validation,
)
from cellforge.splits import SplitColumns, SplitManifest, SplitSpec, apply_split, make_split

COLUMNS = SplitColumns()
N_GENES = 40


def _world(context_scales: dict[str, float] | None = None, seed: int = 0) -> ad.AnnData:
    """Perturbing gene p shifts expression by row p of a low-rank symmetric matrix."""

    context_scales = context_scales or {"ctx": 1.0}
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(N_GENES, 3))
    effect = u @ u.T / 3
    base = rng.normal(size=N_GENES) + 5
    genes = [f"g{i}" for i in range(N_GENES)]
    rows, labels = [], []
    for context, scale in context_scales.items():
        for _ in range(150):
            rows.append(base + rng.normal(scale=0.05, size=N_GENES))
            labels.append((context, "", "non_targeting_control", True))
        for p in range(N_GENES):
            for _ in range(30):
                rows.append(base + scale * effect[p] + rng.normal(scale=0.05, size=N_GENES))
                labels.append((context, genes[p], "single_target", False))
    obs = pd.DataFrame(labels, columns=["context", "target_genes", "assignment_class", "is_control"])
    obs.index = pd.Index([f"c{i}" for i in range(len(obs))])
    var = pd.DataFrame({"gene_symbol": genes}, index=genes)
    return ad.AnnData(X=np.vstack(rows).astype(np.float32), obs=obs, var=var)


@pytest.fixture(scope="module")
def world() -> ad.AnnData:
    return _world()


@pytest.fixture(scope="module")
def manifest(world: ad.AnnData) -> SplitManifest:
    return make_split(world, SplitSpec("unseen_perturbation", seed=0))


def test_metric_known_answers() -> None:
    a = np.array([1.0, 2.0, 3.0])
    assert delta_pearson(a, a) == pytest.approx(1.0)
    assert delta_pearson(a, -a) == pytest.approx(-1.0)
    assert np.isnan(delta_pearson(np.zeros(3), a))
    assert np.isnan(delta_pearson(a, np.ones(3)))
    assert delta_mse(np.zeros(2), np.ones(2)) == pytest.approx(1.0)


def test_control_mean_predicts_no_change_and_pearson_is_undefined(
    world: ad.AnnData, manifest: SplitManifest
) -> None:
    result = evaluate_model(world, manifest, ControlMean())

    assert result.coverage == 1.0
    assert result.undefined_pearson == len(result.scores)
    assert np.isnan(result.mean_pearson_delta)
    assert result.mean_mse_delta > 0


def test_train_mean_shift_equals_mean_training_delta(
    world: ad.AnnData, manifest: SplitManifest
) -> None:
    train = apply_split(world, manifest, "train")
    model = TrainMeanShift()
    model.fit(train, COLUMNS)
    prediction = model.predict(["g0", "g1"])

    pb = pseudobulk(train, COLUMNS)
    expected_delta = (pb.means - pb.control_mean).mean(axis=0)
    for row in prediction.mean_expression:
        np.testing.assert_allclose(row - prediction.control_mean, expected_delta)


def test_embedding_ridge_recovers_structure_that_mean_shift_cannot(
    world: ad.AnnData, manifest: SplitManifest
) -> None:
    mean_shift = evaluate_model(world, manifest, TrainMeanShift())
    ridge = evaluate_model(world, manifest, EmbeddingRidge(alpha=0.1))
    knn = evaluate_model(world, manifest, EmbeddingKNN(k=3))

    assert ridge.mean_pearson_delta > 0.9
    assert ridge.mean_pearson_delta > mean_shift.mean_pearson_delta + 0.3
    assert ridge.mean_mse_delta < mean_shift.mean_mse_delta
    assert knn.coverage == 1.0 and not np.isnan(knn.mean_pearson_delta)


def test_unmeasured_target_gene_falls_back_and_reports_it(
    world: ad.AnnData, manifest: SplitManifest
) -> None:
    train = apply_split(world, manifest, "train")
    ridge, shift = EmbeddingRidge(), TrainMeanShift()
    ridge.fit(train, COLUMNS)
    shift.fit(train, COLUMNS)

    got, base = ridge.predict(["not_a_measured_gene"]), shift.predict(["not_a_measured_gene"])
    assert got.covered == (False,)
    np.testing.assert_allclose(got.mean_expression, base.mean_expression)


def test_evaluation_refuses_a_leaky_manifest(world: ad.AnnData, manifest: SplitManifest) -> None:
    cell = manifest.partitions["test"][0]
    leaky = SplitManifest(
        **{**manifest.__dict__, "partitions": {**manifest.partitions, "train": manifest.partitions["train"] + (cell,)}}
    )
    with pytest.raises(ValueError, match="validation failed"):
        evaluate_model(world, leaky, ControlMean())


def test_incompatible_model_outputs_are_rejected(world: ad.AnnData, manifest: SplitManifest) -> None:
    class ReversedGenes(ControlMean):
        def predict(self, perturbations):
            p = super().predict(perturbations)
            return Predictions(p.perturbations, p.genes[::-1], p.mean_expression, p.control_mean, p.covered)

    class NotFinite(ControlMean):
        def predict(self, perturbations):
            p = super().predict(perturbations)
            return Predictions(
                p.perturbations, p.genes, p.mean_expression * np.nan, p.control_mean, p.covered
            )

    with pytest.raises(ValueError, match="gene order"):
        evaluate_model(world, manifest, ReversedGenes())
    with pytest.raises(ValueError, match="non-finite"):
        evaluate_model(world, manifest, NotFinite())


def test_hyperparameters_are_selected_on_validation_only(
    world: ad.AnnData, manifest: SplitManifest
) -> None:
    best, results = select_by_validation(
        world, manifest, EmbeddingRidge, [{"alpha": 0.1}, {"alpha": 1e6}]
    )
    assert best == {"alpha": 0.1}
    assert results[0][1] > results[1][1]
    with pytest.raises(ValueError, match="grid is empty"):
        select_by_validation(world, manifest, EmbeddingRidge, [])


def test_seen_perturbation_delta_handles_context_shift() -> None:
    data = _world({"ctx_a": 1.0, "ctx_b": 2.0})
    manifest = make_split(
        data, SplitSpec("unseen_context", train_context="ctx_a", test_context="ctx_b")
    )
    seen = evaluate_model(data, manifest, SeenPerturbationDelta())
    shift = evaluate_model(data, manifest, TrainMeanShift())

    assert seen.mean_pearson_delta > 0.95
    assert seen.mean_pearson_delta > shift.mean_pearson_delta + 0.3
    assert seen.coverage == 1.0
