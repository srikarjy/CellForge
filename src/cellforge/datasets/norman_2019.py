"""Norman et al. 2019 CRISPRa Perturb-seq adapter.

The maintained pertpy loader is optional. CellForge accepts a local ``.h5ad``
artifact so benchmark runs can pin and hash the exact data used, while the
adapter normalizes the metadata contract consumed by measurement, splits, and
baselines.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from cellforge.validation import ValidationReport

if TYPE_CHECKING:
    from anndata import AnnData

NORMAN_ACCESSION = "GSE133344"
NORMAN_DOI = "10.1126/science.aax4438"
NORMAN_DATASET_NAME = "norman_2019"


def _is_control(value: str) -> bool:
    return value.strip().lower() in {"ctrl", "control", "ntc", "non-targeting", "non_targeting"}


def _assignment_class(target: str, is_control: bool) -> str:
    if is_control:
        return "non_targeting_control"
    components = [part.strip() for part in target.split("+") if part.strip() and not _is_control(part)]
    return "single_target" if len(components) == 1 else "multi_target"


def normalize_norman(adata: AnnData) -> AnnData:
    """Return a copy with CellForge's shared perturbation metadata columns."""

    data = adata.copy()
    source = data.obs
    if "perturbation_name" in source:
        perturbations = source["perturbation_name"].astype(str)
    elif "guide_identity" in source:
        perturbations = source["guide_identity"].astype(str)
    elif "target_genes" in source:
        perturbations = source["target_genes"].astype(str)
    elif "condition" in source:
        perturbations = source["condition"].astype(str)
    else:
        raise ValueError("Norman AnnData requires perturbation_name, guide_identity, or target_genes")

    if "control" in source:
        controls = source["control"].astype(str).str.lower().isin({"1", "true", "yes"}) | perturbations.map(_is_control)
    elif "perturbation_type" in source:
        type_values = source["perturbation_type"].astype(str).str.lower()
        controls = type_values.isin({"control", "ctrl", "ntc", "non-targeting"}) | perturbations.map(_is_control)
    else:
        controls = perturbations.map(_is_control)
    data.obs["target_genes"] = perturbations.where(~controls, "")
    data.obs["gears_condition"] = perturbations.where(~controls, "ctrl")
    data.obs["target_gene"] = [
        "+".join(part.strip() for part in target.split("+") if part.strip() and not _is_control(part))
        for target in data.obs["target_genes"].astype(str)
    ]
    data.obs["is_control"] = controls.astype(bool)
    target_values = data.obs["target_genes"].astype(str)
    data.obs["assignment_class"] = [
        _assignment_class(target, bool(is_control))
        for target, is_control in zip(target_values, data.obs["is_control"], strict=True)
    ]
    if "context" not in data.obs:
        data.obs["context"] = data.obs["cell_type"].astype(str) if "cell_type" in data.obs else "default"
    data.obs["context"] = data.obs["context"].astype(str)
    data.uns["cellforge_dataset"] = NORMAN_DATASET_NAME
    data.uns["series_accession"] = NORMAN_ACCESSION
    data.uns["source_doi"] = NORMAN_DOI
    data.uns["supported_ood_dimensions"] = ["unseen_perturbation"]
    data.uns["unsupported_ood_dimensions"] = ["unseen_donor", "unseen_cell_type", "unseen_context"]
    return data


def inspect_norman(adata: AnnData) -> ValidationReport:
    """Validate the normalized metadata contract without loading external data."""

    report = ValidationReport(dataset=NORMAN_DATASET_NAME)
    required = ["target_genes", "is_control", "assignment_class", "context"]
    missing = [column for column in required if column not in adata.obs.columns]
    if missing:
        report.add_error("missing_metadata", "Norman metadata contract is incomplete", columns=missing)
        return report
    if adata.n_obs == 0 or adata.n_vars == 0:
        report.add_error("empty_matrix", "Norman AnnData has no cells or genes")
    if adata.obs_names.has_duplicates or adata.var_names.has_duplicates:
        report.add_error("duplicate_identifiers", "Norman cell or gene identifiers are not unique")
    controls = adata.obs["is_control"].to_numpy(dtype=bool)
    perturbations = adata.obs["target_genes"].astype(str)
    report.summary.update(
        {
            "accession": NORMAN_ACCESSION,
            "cells": int(adata.n_obs),
            "genes": int(adata.n_vars),
            "control_cells": int(controls.sum()),
            "perturbations": int(perturbations[~controls].nunique()),
            "combinations": int(adata.obs.loc[adata.obs["assignment_class"].eq("multi_target") & ~controls, "target_genes"].nunique()),
            "supported_ood_dimensions": ["unseen_perturbation"],
            "unsupported_ood_dimensions": ["unseen_donor", "unseen_cell_type", "unseen_context"],
        }
    )
    return report


def load_norman_2019(path: str | Path) -> AnnData:
    """Load and normalize a pinned local Norman ``.h5ad`` artifact."""

    import anndata as ad

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    data = normalize_norman(ad.read_h5ad(path))
    report = inspect_norman(data)
    report.raise_for_errors()
    data.uns["source_artifact_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    data.uns["validation"] = report.to_dict()
    return data


def load_norman_2019_from_pertpy() -> AnnData:
    """Load the maintained pertpy copy; callers must persist/hash the artifact."""

    try:
        import pertpy as pt
    except ImportError as error:
        raise RuntimeError("Install the optional 'singlecell' extra to use the pertpy Norman loader") from error
    return normalize_norman(pt.dt.norman_2019())


def prepare_norman_subset(
    adata: AnnData,
    *,
    max_cells: int = 50_000,
    min_cells_per_perturbation: int = 20,
    seed: int = 0,
) -> AnnData:
    """Create a reproducible subset without consulting model performance."""
    data = normalize_norman(adata)
    if max_cells < 1 or min_cells_per_perturbation < 1:
        raise ValueError("subset limits must be positive")
    obs = data.obs
    control = obs["is_control"].to_numpy(dtype=bool)
    eligible_mask = (~control) & obs["assignment_class"].eq("single_target").to_numpy()
    names = obs.loc[eligible_mask, "target_genes"].astype(str)
    counts = names.value_counts()
    eligible = sorted(counts[counts >= min_cells_per_perturbation].index)
    order = list(np.random.default_rng(seed).permutation(eligible))
    selected: list[str] = []
    used = int(control.sum())
    for name in order:
        count = int(counts[name])
        if selected and used + count > max_cells:
            continue
        if not selected and used + count > max_cells:
            raise ValueError("max_cells is too small for one eligible perturbation plus controls")
        selected.append(name)
        used += count
    if len(selected) < 3:
        raise ValueError("subset needs at least three eligible perturbations")
    keep = control | obs["target_genes"].astype(str).isin(selected).to_numpy()
    subset = data[keep].copy()
    subset.uns["cellforge_norman_subset"] = {
        "selection": "seeded perturbation sampling after minimum cell-count filter",
        "max_cells": max_cells,
        "min_cells_per_perturbation": min_cells_per_perturbation,
        "seed": seed,
        "selected_perturbations": selected,
        "cells": int(subset.n_obs),
    }
    return subset
