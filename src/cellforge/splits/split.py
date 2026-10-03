"""Reproducible, leakage-checked train/validation/test splits for perturbation data.

Two supported holdouts:

* ``unseen_perturbation``: whole perturbations (target genes) are assigned to one
  partition, so no perturbation seen in training appears in validation or test.
  Control cells are split by cell; held-out controls are an evaluation reference
  only and must never be used for fitting.
* ``unseen_context``: train on one biological context, test on another. The
  validation set is a seeded cell-level holdout *within the training context*, so
  it shares perturbations with train and measures in-context fit only.

Donor and cell-type holdouts are intentionally unsupported; add them only when a
dataset genuinely carries that metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pandas as pd

from cellforge.validation import ValidationReport

if TYPE_CHECKING:
    from anndata import AnnData

SplitKind = Literal["unseen_perturbation", "unseen_context"]
PARTITIONS = ("train", "val", "test")


@dataclass(frozen=True)
class SplitColumns:
    """Names of the ``obs`` columns the engine reads; defaults match the Dixit adapter."""

    perturbation: str = "target_genes"
    control: str = "is_control"
    assignment_class: str = "assignment_class"
    eligible_class: str = "single_target"
    context: str = "context"


@dataclass(frozen=True)
class SplitSpec:
    kind: SplitKind
    seed: int = 0
    val_fraction: float = 0.15
    test_fraction: float = 0.25
    min_cells_per_perturbation: int = 20
    train_context: str | None = None
    test_context: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("unseen_perturbation", "unseen_context"):
            raise ValueError(f"Unsupported split kind: {self.kind!r}")
        for name in ("val_fraction", "test_fraction"):
            if not 0 < getattr(self, name) < 0.5:
                raise ValueError(f"{name} must be in (0, 0.5)")
        if self.min_cells_per_perturbation < 1:
            raise ValueError("min_cells_per_perturbation must be at least 1")
        if self.kind == "unseen_context":
            if not self.train_context or not self.test_context:
                raise ValueError("unseen_context requires train_context and test_context")
            if self.train_context == self.test_context:
                raise ValueError("train_context and test_context must differ")


@dataclass(frozen=True)
class SplitManifest:
    spec: dict[str, Any]
    dataset_fingerprint: str
    partitions: dict[str, tuple[str, ...]]
    perturbations: dict[str, tuple[str, ...]]
    counts: dict[str, dict[str, int]]
    excluded: dict[str, int]
    notes: tuple[str, ...]
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec,
            "dataset_fingerprint": self.dataset_fingerprint,
            "partitions": {k: list(v) for k, v in self.partitions.items()},
            "perturbations": {k: list(v) for k, v in self.perturbations.items()},
            "counts": self.counts,
            "excluded": self.excluded,
            "notes": list(self.notes),
            "sha256": self.sha256,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> SplitManifest:
        data = json.loads(text)
        return cls(
            spec=data["spec"],
            dataset_fingerprint=data["dataset_fingerprint"],
            partitions={k: tuple(v) for k, v in data["partitions"].items()},
            perturbations={k: tuple(v) for k, v in data["perturbations"].items()},
            counts=data["counts"],
            excluded=data["excluded"],
            notes=tuple(data["notes"]),
            sha256=data["sha256"],
        )


def dataset_fingerprint(adata: AnnData) -> str:
    """Identity of the data a split was made from (names, shape, and total signal)."""

    digest = hashlib.sha256()
    digest.update("\x1f".join(map(str, adata.obs_names)).encode())
    digest.update(b"\x1e")
    digest.update("\x1f".join(map(str, adata.var_names)).encode())
    total = float(adata.X.sum(dtype=np.float64))
    nnz = getattr(adata.X, "nnz", -1)
    digest.update(f"|{adata.n_obs}x{adata.n_vars}|{nnz}|{total!r}".encode())
    return digest.hexdigest()


def _manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _require_columns(adata: AnnData, spec: SplitSpec, columns: SplitColumns) -> None:
    needed = [columns.perturbation, columns.control, columns.assignment_class]
    if spec.kind == "unseen_context":
        needed.append(columns.context)
    missing = [name for name in needed if name not in adata.obs.columns]
    if missing:
        raise ValueError(f"AnnData.obs is missing required columns: {missing}")


def _split_indices(
    rng: np.random.Generator, indices: np.ndarray, val_fraction: float, test_fraction: float | None
) -> dict[str, np.ndarray]:
    shuffled = indices[rng.permutation(len(indices))]
    n_val = max(1, round(val_fraction * len(shuffled)))
    n_test = max(1, round(test_fraction * len(shuffled))) if test_fraction else 0
    if n_val + n_test >= len(shuffled):
        raise ValueError("Too few control cells to populate every partition")
    out = {"val": shuffled[:n_val], "train": shuffled[n_val + n_test :]}
    if test_fraction:
        out["test"] = shuffled[n_val : n_val + n_test]
    return out


def make_split(
    adata: AnnData, spec: SplitSpec, columns: SplitColumns | None = None
) -> SplitManifest:
    """Build a deterministic split manifest. The same data and spec give the same hash."""

    columns = columns or SplitColumns()
    _require_columns(adata, spec, columns)
    obs = adata.obs
    cells = np.asarray(adata.obs_names, dtype=object)
    is_control = obs[columns.control].to_numpy(dtype=bool)
    perts = obs[columns.perturbation].astype(str).to_numpy()
    eligible = (obs[columns.assignment_class] == columns.eligible_class).to_numpy() & ~is_control
    rng = np.random.default_rng(spec.seed)
    part = np.full(len(cells), "", dtype=object)
    excluded = {"ineligible_cells": int((~eligible & ~is_control).sum())}
    notes: list[str] = []

    if spec.kind == "unseen_perturbation":
        counts = pd.Series(perts[eligible]).value_counts()
        small = counts[counts < spec.min_cells_per_perturbation]
        keep = sorted(counts[counts >= spec.min_cells_per_perturbation].index)
        excluded["perturbations_below_min_cells"] = len(small)
        excluded["cells_in_small_perturbations"] = int(small.sum())
        if len(keep) < 3:
            raise ValueError("Need at least 3 perturbations meeting min_cells_per_perturbation")
        order = rng.permutation(len(keep))
        n_test = max(1, round(spec.test_fraction * len(keep)))
        n_val = max(1, round(spec.val_fraction * len(keep)))
        if n_test + n_val >= len(keep):
            raise ValueError("Too few perturbations to populate train, val, and test")
        owner = {}
        for rank, index in enumerate(order):
            owner[keep[index]] = (
                "test" if rank < n_test else "val" if rank < n_test + n_val else "train"
            )
        for position in np.flatnonzero(eligible):
            part[position] = owner.get(perts[position], "")
        control_split = _split_indices(
            rng, np.flatnonzero(is_control), spec.val_fraction, spec.test_fraction
        )
        for name, positions in control_split.items():
            part[positions] = name
        perturbations = {
            name: tuple(sorted(p for p, o in owner.items() if o == name)) for name in PARTITIONS
        }
        notes.append("Held-out controls are an evaluation reference only; never fit on them.")
    else:
        context = obs[columns.context].astype(str).to_numpy()
        train_ctx, test_ctx = str(spec.train_context), str(spec.test_context)
        per_ctx = {}
        for ctx in (train_ctx, test_ctx):
            counts = pd.Series(perts[eligible & (context == ctx)]).value_counts()
            per_ctx[ctx] = counts[counts >= spec.min_cells_per_perturbation].index
        keep = sorted(set(per_ctx[train_ctx]) & set(per_ctx[test_ctx]))
        if not keep:
            raise ValueError("No perturbation meets min_cells_per_perturbation in both contexts")
        shared = np.isin(perts, keep)
        excluded["perturbed_cells_outside_shared_perturbations"] = int(
            (eligible & ~shared & np.isin(context, [train_ctx, test_ctx])).sum()
        )
        train_pool = np.flatnonzero((eligible & shared | is_control) & (context == train_ctx))
        split = _split_indices(rng, train_pool, spec.val_fraction, None)
        part[split["train"]] = "train"
        part[split["val"]] = "val"
        part[np.flatnonzero((eligible & shared | is_control) & (context == test_ctx))] = "test"
        perturbations = {name: tuple(keep) for name in PARTITIONS}
        notes.append(
            "Validation is a cell-level holdout within the training context; it shares "
            "perturbations with train and does not measure generalization."
        )

    partitions = {name: tuple(cells[part == name]) for name in PARTITIONS}
    counts_out = {
        name: {
            "cells": int((part == name).sum()),
            "control_cells": int(((part == name) & is_control).sum()),
            "perturbations": len(perturbations[name]),
        }
        for name in PARTITIONS
    }
    payload: dict[str, Any] = {
        "spec": asdict(spec),
        "dataset_fingerprint": dataset_fingerprint(adata),
        "partitions": {k: list(v) for k, v in partitions.items()},
        "perturbations": {k: list(v) for k, v in perturbations.items()},
        "counts": counts_out,
        "excluded": excluded,
        "notes": notes,
    }
    return SplitManifest(
        spec=payload["spec"],
        dataset_fingerprint=payload["dataset_fingerprint"],
        partitions=partitions,
        perturbations=perturbations,
        counts=counts_out,
        excluded=excluded,
        notes=tuple(notes),
        sha256=_manifest_hash(payload),
    )


def check_leakage(
    adata: AnnData, manifest: SplitManifest, columns: SplitColumns | None = None
) -> ValidationReport:
    """Independently re-verify a manifest against the data; any error means do not trust it."""

    columns = columns or SplitColumns()
    report = ValidationReport(dataset="split_manifest")
    obs = adata.obs
    kind = manifest.spec["kind"]
    report.summary.update({"kind": kind, "counts": manifest.counts, "excluded": manifest.excluded})

    payload = manifest.to_dict()
    if _manifest_hash(payload) != manifest.sha256:
        report.add_error("manifest_hash_mismatch", "Manifest content does not match its hash")
    if manifest.dataset_fingerprint != dataset_fingerprint(adata):
        report.add_error("dataset_mismatch", "Split was made from different data than supplied")
        return report

    known = set(map(str, adata.obs_names))
    seen: dict[str, str] = {}
    for name, members in manifest.partitions.items():
        unknown = [c for c in members if c not in known]
        if unknown:
            report.add_error("unknown_cells", f"{name} has cells absent from the data", count=len(unknown))
        for cell in members:
            if cell in seen:
                report.add_error(
                    "cell_overlap", "A cell appears in two partitions", cells=[cell], partitions=[seen[cell], name]
                )
                break
            seen[cell] = name

    is_control = obs[columns.control].to_numpy(dtype=bool)
    perts = obs[columns.perturbation].astype(str)
    controls_by_cell = dict(zip(map(str, obs.index), is_control))
    pert_by_cell = dict(zip(map(str, obs.index), perts))
    for name, members in manifest.partitions.items():
        if not any(controls_by_cell.get(c, False) for c in members):
            report.add_error("no_controls", f"{name} contains no control cells")

    if kind == "unseen_perturbation":
        declared = {n: set(manifest.perturbations[n]) for n in PARTITIONS}
        for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
            shared = declared[a] & declared[b]
            if shared:
                report.add_error(
                    "perturbation_leakage", f"{a} and {b} share perturbations", perturbations=sorted(shared)[:5]
                )
        for name, members in manifest.partitions.items():
            actual = {pert_by_cell[c] for c in members if c in pert_by_cell and not controls_by_cell[c]}
            stray = actual - declared[name]
            if stray:
                report.add_error(
                    "undeclared_perturbation", f"{name} contains perturbations not declared for it", perturbations=sorted(stray)[:5]
                )
    else:
        context = dict(zip(map(str, obs.index), obs[columns.context].astype(str)))
        expected = {
            "train": manifest.spec["train_context"],
            "val": manifest.spec["train_context"],
            "test": manifest.spec["test_context"],
        }
        for name, members in manifest.partitions.items():
            wrong = [c for c in members if context.get(c) != expected[name]]
            if wrong:
                report.add_error("context_leakage", f"{name} contains cells from the wrong context", count=len(wrong))
    return report


def apply_split(adata: AnnData, manifest: SplitManifest, partition: str) -> AnnData:
    """Return the cells of one partition as an AnnData copy."""

    if partition not in PARTITIONS:
        raise ValueError(f"Unknown partition {partition!r}; expected one of {PARTITIONS}")
    return adata[list(manifest.partitions[partition])].copy()
