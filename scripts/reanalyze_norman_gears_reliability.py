#!/usr/bin/env python
"""Recompute historical GEARS trust with validated split-half reliability."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cellforge.datasets import load_norman_2019
from cellforge.reliability import SplitHalfConfig, classify_anndata


def _status(row: pd.Series, reliability: str) -> tuple[str, str]:
    advanced = float(row["advanced_score"])
    linear = float(row["linear_score"])
    control = float(row["control_score"])
    training = float(row["training_mean_score"])
    if pd.isna(advanced) or pd.isna(linear):
        return "UNKNOWN", "At least one matched metric is undefined."
    if not pd.isna(control) and advanced <= control:
        return "UNTRUSTED", "Advanced model does not beat the no-change baseline."
    if reliability != "SPECIFIC":
        return "LIMITED", f"Measurement reliability is {reliability}."
    if advanced <= linear:
        return "LIMITED", "Model beats no-change baseline but not the linear baseline."
    if not pd.isna(training) and advanced <= training:
        return "LIMITED", "Model beats no-change and linear baselines but not the training-mean baseline."
    return "TRUSTED", "Model beats all declared baselines on this matched perturbation."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--historical-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data = load_norman_2019(args.dataset)
    reliability = classify_anndata(
        data,
        SplitHalfConfig(perturbation_column="target_gene", control_column="is_control", context_column="context", seed=17),
    )
    old = pd.read_parquet(args.historical_artifact / "trust" / "model_trust.parquet")
    records = {record.perturbation: record for record in reliability}
    rows = []
    for _, row in old.iterrows():
        record = records[row["perturbation"]]
        new_status, reason = _status(row, record.classification.value)
        rows.append({
            "perturbation": row["perturbation"],
            "old_reliability": row["measurement_reliability"],
            "new_reliability": record.classification.value,
            "rho": record.reliability_statistic,
            "median_split_correlation": record.median_split_correlation,
            "shared_cosine": record.shared_cosine,
            "advanced_score": row["advanced_score"],
            "linear_score": row["linear_score"],
            "training_mean_score": row["training_mean_score"],
            "old_trust_status": row["trust_status"],
            "new_trust_status": new_status,
            "new_trust_reason": reason,
        })
    result = pd.DataFrame(rows).sort_values("perturbation")
    result.to_csv(args.output / "comparison.csv", index=False)
    summary = {
        "historical_artifact": str(args.historical_artifact),
        "reliability_method": "published_split_half_spearman_brown_v1",
        "config": SplitHalfConfig().__dict__,
        "old_trust_counts": result["old_trust_status"].value_counts().to_dict(),
        "new_trust_counts": result["new_trust_status"].value_counts().to_dict(),
        "changed_reliability": int((result.old_reliability != result.new_reliability).sum()),
        "changed_trust": int((result.old_trust_status != result.new_trust_status).sum()),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
