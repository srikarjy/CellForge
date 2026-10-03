"""Minimal CLI for inspecting reproducible CellForge artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cellforge", description="Inspect CellForge decision artifacts")
    sub = parser.add_subparsers(dest="command")
    info = sub.add_parser("package-info", help="summarize a DecisionPackage JSON artifact")
    info.add_argument("path", type=Path)
    run = sub.add_parser("run-model", help="run one optional advanced model on a pinned Norman artifact")
    run.add_argument("--dataset", required=True, type=Path, help="normalized Norman .h5ad path")
    run.add_argument("--model", choices=("gears",), default="gears")
    run.add_argument("--output", type=Path, default=Path("artifacts/model-run"))
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--max-cells", type=int, default=50_000)
    run.add_argument("--min-cells-per-perturbation", type=int, default=20)
    run.add_argument("--config", type=Path, help="JSON model configuration")
    args = parser.parse_args(argv)
    if args.command == "package-info":
        payload = json.loads(args.path.read_text())
        print(json.dumps({"run_id": payload.get("run_id"), "status": payload.get("status"), "candidates": len(payload.get("candidates", [])), "package_sha256": payload.get("package_sha256")}, indent=2))
        return 0
    if args.command == "run-model":
        from dataclasses import asdict

        from cellforge.baselines import ControlMean, EmbeddingRidge, TrainMeanShift
        from cellforge.datasets.norman_2019 import load_norman_2019, prepare_norman_subset
        from cellforge.evaluation import evaluate_model
        from cellforge.models import GEARSAdapter
        from cellforge.splits import SplitSpec, make_split

        adata = prepare_norman_subset(
            load_norman_2019(args.dataset),
            max_cells=args.max_cells,
            min_cells_per_perturbation=args.min_cells_per_perturbation,
            seed=args.seed,
        )
        spec = SplitSpec(kind="unseen_perturbation", seed=args.seed)
        manifest = make_split(adata, spec)
        config = json.loads(args.config.read_text()) if args.config else {}
        models = {
            "control_mean": ControlMean(),
            "train_mean_shift": TrainMeanShift(),
            "embedding_ridge": EmbeddingRidge(),
            "gears": GEARSAdapter(config=config, seed=args.seed),
        }
        args.output.mkdir(parents=True, exist_ok=True)
        results = {name: asdict(evaluate_model(adata, manifest, model)) for name, model in models.items()}
        (args.output / "split_manifest.json").write_text(manifest.to_json() + "\n")
        (args.output / "metrics.json").write_text(json.dumps(results, sort_keys=True, indent=2, default=str) + "\n")
        print(json.dumps({"model": args.model, "output": str(args.output), "split_sha256": manifest.sha256}, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
