#!/usr/bin/env python
"""Validate CellForge reliability against the published split-half method."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cellforge.reliability import SplitHalfConfig, classify_anndata
from cellforge.reliability.split_half import _classify, _dense, _split_half, _spearman_brown


def _records(data: Path, config: SplitHalfConfig) -> pd.DataFrame:
    rows = [record.to_dict() for record in classify_anndata(ad.read_h5ad(data), config)]
    return pd.DataFrame(rows).sort_values(["context", "perturbation"]).reset_index(drop=True)


def _bootstrap(data: Path, names: list[str], config: SplitHalfConfig, repeats: int) -> pd.DataFrame:
    source = ad.read_h5ad(data)
    labels = source.obs[config.perturbation_column].astype(str).to_numpy()
    contexts = source.obs[config.context_column].astype(str).to_numpy()
    controls = source.obs[config.control_column].to_numpy(dtype=bool)
    matrix = _dense(source.X)
    rows: list[dict[str, object]] = []
    for name in names:
        context = contexts[labels == name][0]
        control = matrix[(contexts == context) & controls]
        pert = matrix[(contexts == context) & ~controls & (labels == name)]
        gene_idx = np.argsort(control.mean(axis=0))[-config.expressed_genes :]
        control = control[:, gene_idx]
        pert = pert[:, gene_idx]
        n = min(len(pert) // 2, len(control) // 2)
        if n < config.min_cells:
            continue
        name_seed = int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "little")
        rng = np.random.default_rng(config.seed + name_seed)
        classes: list[str] = []
        statistics: list[float] = []
        for _ in range(repeats):
            p_idx = rng.integers(0, len(pert), len(pert))
            c_idx = rng.integers(0, len(control), len(control))
            median_r, _, _ = _split_half(
                pert[p_idx], control[c_idx], n_half=n, repeats=config.repeats, seed=int(rng.integers(0, 2**31 - 1))
            )
            reliability = _spearman_brown(median_r)
            statistics.append(reliability)
            classes.append(_classify(reliability, None, config).value)
        rows.append({
            "perturbation": name,
            "bootstrap_repeats": repeats,
            "reliability_mean": float(np.mean(statistics)),
            "reliability_std": float(np.std(statistics)),
            "classification_mode": Counter(classes).most_common(1)[0][0],
            "classification_stability": float(max(Counter(classes).values()) / len(classes)),
            "classification_counts": dict(Counter(classes)),
        })
    return pd.DataFrame(rows)


def _plot_diagnostics(frame: pd.DataFrame, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    frame = frame.copy()
    frame["control_noise_proxy"] = 1.0 - frame["reliability"].clip(0, 1)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    axes[0, 0].scatter(frame["control_noise_proxy"], frame["response_magnitude"], c=frame["reliability"], cmap="viridis")
    axes[0, 0].set(xlabel="1 - split-half reliability", ylabel="response magnitude", title="Response vs reliability diagnostic")
    axes[0, 1].hist(frame["reliability"].dropna(), bins=20, color="#496a81")
    axes[0, 1].axvline(0.5, color="#c0392b", linestyle="--", label="published rho = 0.5")
    axes[0, 1].set(xlabel="Spearman–Brown reliability", ylabel="perturbations", title="Reliability distribution")
    axes[0, 1].legend()
    axes[1, 0].scatter(frame["reliability"], frame["response_magnitude"], s=np.maximum(frame["cells"], 10) / 5, alpha=0.7)
    axes[1, 0].set(xlabel="reliability", ylabel="response magnitude", title="Magnitude vs reliability")
    axes[1, 1].scatter(frame["cells"], frame["reliability"], c=frame["response_magnitude"], cmap="plasma", alpha=0.75)
    axes[1, 1].set(xlabel="cells per perturbation", ylabel="reliability", title="Reliability vs cell count")
    fig.savefig(output / "reliability_diagnostics.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(frame["median_split_correlation"].dropna(), bins=20, color="#7f8c8d")
    ax.set(xlabel="median split-half Pearson correlation", ylabel="perturbations", title="Split-half control/perturbation agreement")
    fig.savefig(output / "split_half_correlation_distribution.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_control_distribution(data: Path, output: Path, expressed_genes: int) -> None:
    source = ad.read_h5ad(data)
    controls = source.obs["is_control"].to_numpy(dtype=bool)
    matrix = _dense(source.X)[controls]
    gene_idx = np.argsort(matrix.mean(axis=0))[-expressed_genes:]
    per_gene_sd = matrix[:, gene_idx].std(axis=0)
    pd.DataFrame({"control_gene_sd": per_gene_sd}).to_csv(output / "control_noise_distribution.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(per_gene_sd, bins=30, color="#8e6c8c")
    ax.set(xlabel="control-cell standard deviation", ylabel="genes", title="Empirical control noise distribution")
    fig.savefig(output / "control_noise_distribution.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--small", type=Path, required=True)
    parser.add_argument("--large", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=50)
    args = parser.parse_args()
    config = SplitHalfConfig(repeats=100, expressed_genes=1000, min_cells=8, seed=17)
    args.output.mkdir(parents=True, exist_ok=True)
    small = _records(args.small, config)
    large = _records(args.large, config)
    small.to_csv(args.output / "small_records.csv", index=False)
    large.to_csv(args.output / "large_records.csv", index=False)
    merged = small.merge(large, on=["perturbation", "context"], suffixes=("_small", "_large"))
    merged["class_agreement"] = merged["classification_small"] == merged["classification_large"]
    merged["reliability_difference"] = merged["reliability_large"] - merged["reliability_small"]
    merged.to_csv(args.output / "sample_size_comparison.csv", index=False)
    selected = [name for name in ["CEBPA", "SAMD1", "FOXF1", "CDKN1B"] if name in set(small.perturbation)]
    bootstrap = _bootstrap(args.small, selected, config, args.repeats)
    bootstrap.to_json(args.output / "bootstrap.json", orient="records", indent=2)
    _plot_diagnostics(small, args.output)
    _plot_control_distribution(args.small, args.output, config.expressed_genes)
    summary = {
        "method": config.method,
        "config": config.__dict__,
        "small_counts": small["classification"].value_counts().to_dict(),
        "large_counts": large["classification"].value_counts().to_dict(),
        "small_proportions": small["classification"].value_counts(normalize=True).to_dict(),
        "large_proportions": large["classification"].value_counts(normalize=True).to_dict(),
        "shared_perturbations": int(len(merged)),
        "class_agreement": float(merged["class_agreement"].mean()) if len(merged) else None,
        "reliability_correlation": float(merged["reliability_small"].corr(merged["reliability_large"])) if len(merged) > 1 else None,
        "bootstrap": bootstrap.to_dict(orient="records"),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
