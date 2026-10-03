#!/usr/bin/env python
"""Prepare a deterministic single-target Norman subset from GEARS' real H5AD."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import scanpy as sc

from cellforge.datasets.norman_2019 import normalize_norman


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="real GEARS perturb_processed.h5ad")
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-cells", type=int, default=20_000)
    parser.add_argument("--min-cells-per-perturbation", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    backed = sc.read_h5ad(args.source, backed="r")
    obs = backed.obs
    controls = obs["condition"].astype(str).eq("ctrl").to_numpy()
    conditions = obs["condition"].astype(str)
    single = (~controls) & conditions.map(
        lambda value: sum(part.strip().lower() not in {"ctrl", "control", "ntc", "non-targeting", "non_targeting"} for part in value.split("+")) == 1
    ).to_numpy()
    counts = conditions[single].value_counts()
    eligible = sorted(counts[counts >= args.min_cells_per_perturbation].index)
    order = list(np.random.default_rng(args.seed).permutation(eligible))
    selected, used = [], int(controls.sum())
    for condition in order:
        count = int(counts[condition])
        if selected and used + count > args.max_cells:
            continue
        if not selected and used + count > args.max_cells:
            raise ValueError("max-cells is too small for controls plus one perturbation")
        selected.append(condition)
        used += count
    if len(selected) < 3:
        raise ValueError("at least three eligible single-target perturbations are required")
    keep = controls | conditions.isin(selected).to_numpy()
    subset = normalize_norman(backed[keep].to_memory())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subset.write_h5ad(args.output)
    manifest = {
        "source": str(args.source),
        "source_size_bytes": args.source.stat().st_size,
        "source_sha256": _sha256(args.source),
        "output": str(args.output),
        "output_sha256": _sha256(args.output),
        "selection": "single-target conditions (one non-control component), seeded order, cell budget",
        "seed": args.seed,
        "max_cells": args.max_cells,
        "min_cells_per_perturbation": args.min_cells_per_perturbation,
        "cells": int(subset.n_obs),
        "genes": int(subset.n_vars),
        "control_cells": int(subset.obs["is_control"].sum()),
        "perturbations": selected,
        "excluded_conditions": sorted(set(map(str, conditions.unique())) - set(selected) - {"ctrl"}),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
