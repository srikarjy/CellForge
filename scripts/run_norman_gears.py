#!/usr/bin/env python
"""Run the first real single-target Norman/GEARS CellForge experiment."""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import torch

from cellforge.baselines import ControlMean, EmbeddingRidge, TrainMeanShift
from cellforge.datasets import load_norman_2019
from cellforge.evidence import EvidenceDirection, EvidenceType, normalize_evidence
from cellforge.evaluation import evaluate_model
from cellforge.measure import MeasurementConfig
from cellforge.models import GEARSAdapter
from cellforge.prioritize import CandidateEvaluation, rank_candidates
from cellforge.trust import ModelTrustStatus
from cellforge.reliability import ReliabilityClass
from cellforge.reliability import SplitHalfConfig
from cellforge.splits import SplitColumns, SplitSpec, make_split
from cellforge.workflow import run_norman_decision


def _json(value):
    return json.dumps(value, sort_keys=True, indent=2, default=str) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gears-data-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--test-batch-size", type=int, default=128)
    parser.add_argument("--fixture-evidence", type=Path)
    parser.add_argument(
        "--reliability-method",
        choices=("legacy_similarity_signal_v1", "published_split_half_spearman_brown_v1"),
        default="published_split_half_spearman_brown_v1",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    columns = SplitColumns(perturbation="target_gene")
    adata = load_norman_2019(args.dataset)
    split = make_split(adata, SplitSpec(kind="unseen_perturbation", seed=args.seed, min_cells_per_perturbation=20), columns)
    (args.output / "split_manifest.json").write_text(split.to_json() + "\n")
    (args.output / "dataset_manifest.json").write_text(_json({"accession": adata.uns.get("series_accession"), "dataset": adata.uns.get("cellforge_dataset"), "shape": adata.shape, "source_artifact_sha256": adata.uns.get("source_artifact_sha256"), "target_column": columns.perturbation, "single_target_only": True}))

    baseline_dir = args.output / "baselines"
    baseline_dir.mkdir(exist_ok=True)
    baseline_models = (ControlMean(), TrainMeanShift(), EmbeddingRidge(gene_symbol_column="gene_name"))
    baseline_results = {}
    for model in baseline_models:
        result = evaluate_model(adata, split, model, columns)
        baseline_results[model.name] = result
    (baseline_dir / "metrics.json").write_text(_json({name: {"aggregate": {"mean_pearson_delta": result.mean_pearson_delta, "mean_mse_delta": result.mean_mse_delta, "undefined_pearson": result.undefined_pearson, "coverage": result.coverage}, "scores": [asdict(score) for score in result.scores]} for name, result in baseline_results.items()}))
    pd.DataFrame([asdict(score) | {"model": name} for name, result in baseline_results.items() for score in result.scores]).to_parquet(baseline_dir / "per_perturbation.parquet", index=False)

    gears_dir = args.output / "gears"
    gears_dir.mkdir(exist_ok=True)
    gears_config = {"device": "cuda" if torch.cuda.is_available() else "cpu", "epochs": args.epochs, "hidden_size": args.hidden_size, "batch_size": args.batch_size, "test_batch_size": args.test_batch_size, "go_workers": 1, "checkpoint_path": str(gears_dir / "model.pt")}
    (gears_dir / "config.json").write_text(_json(gears_config))
    gears = GEARSAdapter(data_dir=str(args.gears_data_dir), config=gears_config, seed=args.seed)
    started = time.time()
    gears_result = evaluate_model(adata, split, gears, columns)
    elapsed = time.time() - started
    (gears_dir / "metrics.json").write_text(_json({"evaluation": {"aggregate": {"mean_pearson_delta": gears_result.mean_pearson_delta, "mean_mse_delta": gears_result.mean_mse_delta, "undefined_pearson": gears_result.undefined_pearson, "coverage": gears_result.coverage}, "scores": [asdict(score) for score in gears_result.scores]}, "training_seconds_and_inference": elapsed}))
    prediction_rows = pd.DataFrame(gears_result.prediction_deltas, index=[score.perturbation for score in gears_result.scores], columns=adata.var_names)
    prediction_rows.to_parquet(gears_dir / "predictions.parquet")
    pd.DataFrame(gears_result.observed_deltas, index=prediction_rows.index, columns=prediction_rows.columns).to_parquet(gears_dir / "observed_deltas.parquet")
    (gears_dir / "checkpoint_manifest.json").write_text(_json({"model": gears_result.model_metadata, "device": gears_config["device"], "python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))

    evidence = []
    if args.fixture_evidence:
        for record in json.loads(args.fixture_evidence.read_text()):
            evidence.append(normalize_evidence(source=record["source"], source_id=record["source_id"], target=record["target"], claim=record["claim"], evidence_type=EvidenceType(record["evidence_type"]), direction=EvidenceDirection(record["direction"]), payload=record["payload"], limitations=("fixture evidence; not a live biological retrieval",)))
    run = run_norman_decision(
        adata,
        advanced=gears_result,
        control=baseline_results["control_mean"],
        linear=baseline_results["embedding_ridge"],
        training_mean=baseline_results["train_mean_shift"],
        evidence=tuple(evidence),
        run_id=args.output.name,
        measurement_config=MeasurementConfig(columns=columns),
        reliability_method=args.reliability_method,
        split_half_config=SplitHalfConfig(
            perturbation_column=columns.perturbation,
            control_column=columns.control,
            context_column="context",
            seed=args.seed,
        ),
    )
    reliability_dir = args.output / "reliability"
    reliability_dir.mkdir(exist_ok=True)
    pd.DataFrame([asdict(record) for record in run.reliability]).to_parquet(reliability_dir / "reliability.parquet", index=False)
    trust_dir = args.output / "trust"
    trust_dir.mkdir(exist_ok=True)
    pd.DataFrame([asdict(record) for record in run.model_trust]).to_parquet(trust_dir / "model_trust.parquet", index=False)
    contradiction_dir = args.output / "contradictions"
    contradiction_dir.mkdir(exist_ok=True)
    (contradiction_dir / "contradictions.json").write_text(_json([asdict(record) for record in run.contradictions]))
    prioritization_dir = args.output / "prioritization"
    prioritization_dir.mkdir(exist_ok=True)
    (prioritization_dir / "candidates.json").write_text(_json([asdict(record) for record in run.ranked]))
    reliability_by_name = {record.perturbation: record for record in run.reliability}
    response_by_name = {record.perturbation: record for record in run.measurement.responses}
    fixture_ids = {record.target: record.source_id for record in evidence}
    without_model = []
    for perturbation in split.perturbations["test"]:
        response = response_by_name[perturbation]
        without_model.append(CandidateEvaluation(
            candidate_id=f"{args.output.name}:{perturbation}",
            perturbation=perturbation,
            target=perturbation,
            context=response.context,
            reliability=reliability_by_name.get(perturbation, None).classification if perturbation in reliability_by_name else ReliabilityClass.INSUFFICIENT_DATA,
            model_trust=ModelTrustStatus.UNKNOWN,
            response_strength=min(1.0, response.effect_magnitude),
            evidence_support=1.0 if perturbation in fixture_ids else 0.0,
            missing_evidence_count=0 if perturbation in fixture_ids else 1,
            evidence_ids=(fixture_ids[perturbation],) if perturbation in fixture_ids else (),
        ))
    (prioritization_dir / "ranking_comparison.json").write_text(_json({"without_gears": [item.candidate_id for item in rank_candidates(tuple(without_model))], "with_gears": [item.candidate_id for item in run.ranked]}))
    decision_dir = args.output / "decision"
    decision_dir.mkdir(exist_ok=True)
    (decision_dir / "package.json").write_text(run.package.to_json())

    figures_dir = args.output / "figures"
    figures_dir.mkdir(exist_ok=True)
    from cellforge.viz import model_failure_analysis, model_reality_check, perturbation_trust_map
    trust_by_name = {record.perturbation: record for record in run.model_trust}
    perturbation_trust_map(run.measurement.responses, run.reliability, trust_by_name).write_html(figures_dir / "trust_map.html", include_plotlyjs="cdn")
    model_reality_check(run.model_trust).write_html(figures_dir / "model_reality_check.html", include_plotlyjs="cdn")
    model_failure_analysis(run.model_trust).write_html(figures_dir / "failure_analysis.html", include_plotlyjs="cdn")
    run_manifest = {"run_id": args.output.name, "dataset": str(args.dataset), "output": str(args.output), "seed": args.seed, "test_perturbations": list(split.perturbations["test"]), "gears_model": gears_result.model_metadata, "baseline_means": {name: result.mean_pearson_delta for name, result in baseline_results.items()}, "gears_mean_pearson_delta": gears_result.mean_pearson_delta, "package_sha256": run.package.sha256, "external_evidence_mode": "fixture" if evidence else "none", "training_seconds_and_inference": elapsed, "reliability_method": args.reliability_method, "reliability_config": run.reliability[0].config if run.reliability else {}}
    (args.output / "run_manifest.json").write_text(_json(run_manifest))
    print(_json(run_manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
