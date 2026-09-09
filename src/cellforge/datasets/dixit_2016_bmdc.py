"""Ingestion and source validation for the Dixit et al. BMDC Perturb-seq data."""

from __future__ import annotations

import csv
import gzip
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from cellforge.validation import ValidationReport

if TYPE_CHECKING:
    from anndata import AnnData

DixitCondition = Literal["unstimulated_0h", "lps_3h"]


@dataclass(frozen=True)
class ConditionFiles:
    sample_accession: str
    context: DixitCondition
    matrix: str
    cells: str
    genes: str
    assignments: str


CONDITION_FILES: dict[DixitCondition, ConditionFiles] = {
    "unstimulated_0h": ConditionFiles(
        sample_accession="GSM2396857",
        context="unstimulated_0h",
        matrix="GSM2396857_dc_0hr.mtx.txt.gz",
        cells="GSM2396857_dc_0hr_cellnames.csv.gz",
        genes="GSM2396857_dc_0hr_genenames.csv.gz",
        assignments="GSM2396857_dc_0hr_cbc_gbc_dict.csv.gz",
    ),
    "lps_3h": ConditionFiles(
        sample_accession="GSM2396856",
        context="lps_3h",
        matrix="GSM2396856_dc_3hr.mtx.txt.gz",
        cells="GSM2396856_dc_3hr_cellnames.csv.gz",
        genes="GSM2396856_dc_3hr_genenames.csv.gz",
        assignments="GSM2396856_dc_3hr_cbc_gbc_dict_strict.csv.gz",
    ),
}

_ENSEMBL_MOUSE_PATTERN = re.compile(r"^ENSMUSG\d+$")


def _read_index(path: Path) -> list[str]:
    with gzip.open(path, "rt", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != ["", "0"]:
        raise ValueError(f"Unexpected indexed CSV header in {path}")
    if any(len(row) != 2 for row in rows[1:]):
        raise ValueError(f"Unexpected indexed CSV row in {path}")
    return [row[1] for row in rows[1:]]


def _read_assignments(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    by_cell: dict[str, list[str]] = defaultdict(list)
    by_guide: dict[str, list[str]] = {}
    with gzip.open(path, "rt", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) != 2:
                raise ValueError(f"Unexpected guide-assignment row in {path}")
            guide, packed_cells = row
            cells = [cell.strip() for cell in packed_cells.split(",") if cell.strip()]
            by_guide[guide] = cells
            for cell in cells:
                by_cell[cell].append(guide)
    return dict(by_cell), by_guide


def _matrix_shape(path: Path) -> tuple[int, int, int]:
    with gzip.open(path, "rt") as handle:
        banner = handle.readline().strip()
        if not banner.startswith("%%MatrixMarket matrix coordinate"):
            raise ValueError(f"Unexpected Matrix Market banner in {path}")
        line = handle.readline()
        while line.startswith("%"):
            line = handle.readline()
        values = line.split()
    if len(values) != 3:
        raise ValueError(f"Missing Matrix Market dimensions in {path}")
    return tuple(int(value) for value in values)  # type: ignore[return-value]


def _parse_gene(value: str) -> tuple[str, str]:
    ensembl_id, separator, symbol = value.partition("_")
    if not separator or not symbol:
        raise ValueError(f"Gene identifier lacks symbol suffix: {value}")
    return ensembl_id, symbol


def _target_for_guide(guide: str) -> str:
    if "NTC" in guide:
        return "NTC"
    parts = guide.split("_")
    if len(parts) < 3 or parts[0] != "m" or not parts[1]:
        raise ValueError(f"Unexpected guide identifier: {guide}")
    return parts[1]


def _assignment_class(guides: list[str]) -> str:
    if not guides:
        return "unassigned"
    targets = {_target_for_guide(guide) for guide in guides}
    if targets == {"NTC"}:
        return "non_targeting_control"
    targets.discard("NTC")
    if len(targets) == 1:
        return "single_target"
    return "multi_target"


def inspect_dixit_bmdc(root: str | Path) -> ValidationReport:
    """Validate released files without loading the full count matrices."""

    root = Path(root)
    report = ValidationReport(dataset="dixit_2016_bmdc")
    condition_summaries: dict[str, object] = {}
    targets_by_context: dict[str, set[str]] = {}
    genes_by_context: dict[str, set[str]] = {}

    for context, files in CONDITION_FILES.items():
        paths = {
            "matrix": root / files.matrix,
            "cells": root / files.cells,
            "genes": root / files.genes,
            "assignments": root / files.assignments,
        }
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            report.add_error(
                "missing_source_files",
                f"{context} is missing required source files",
                files=missing,
            )
            continue

        try:
            n_genes, n_cells, n_nonzero = _matrix_shape(paths["matrix"])
            cells = _read_index(paths["cells"])
            genes = _read_index(paths["genes"])
            by_cell, by_guide = _read_assignments(paths["assignments"])
        except (OSError, UnicodeError, ValueError) as error:
            report.add_error("unreadable_source", str(error), context=context)
            continue

        if n_cells != len(cells) or n_genes != len(genes):
            report.add_error(
                "matrix_index_mismatch",
                "Matrix dimensions do not match cell/gene index lengths",
                context=context,
                matrix_cells=n_cells,
                indexed_cells=len(cells),
                matrix_genes=n_genes,
                indexed_genes=len(genes),
            )
        if len(cells) != len(set(cells)):
            report.add_error("duplicate_cell_ids", "Cell identifiers are not unique", context=context)
        if len(genes) != len(set(genes)):
            report.add_error("duplicate_gene_ids", "Gene identifiers are not unique", context=context)

        invalid_genes = []
        for gene in genes:
            try:
                ensembl_id, _ = _parse_gene(gene)
            except ValueError:
                invalid_genes.append(gene)
                continue
            if not _ENSEMBL_MOUSE_PATTERN.fullmatch(ensembl_id):
                invalid_genes.append(gene)
        if invalid_genes:
            report.add_error(
                "invalid_gene_ids",
                "Gene identifiers do not match expected mouse Ensembl IDs with symbols",
                context=context,
                count=len(invalid_genes),
                examples=invalid_genes[:5],
            )

        invalid_guides = []
        for guide in by_guide:
            try:
                _target_for_guide(guide)
            except ValueError:
                invalid_guides.append(guide)
        if invalid_guides:
            report.add_error(
                "invalid_guide_ids",
                "Guide identifiers do not match the expected release format",
                context=context,
                examples=invalid_guides[:5],
            )

        cell_set = set(cells)
        assigned_cells = set(by_cell)
        unknown_assignment_cells = assigned_cells - cell_set
        if unknown_assignment_cells:
            report.add_warning(
                "assignments_without_expression",
                "Guide assignments include barcodes absent from the expression matrix",
                context=context,
                count=len(unknown_assignment_cells),
            )

        known_assignments = assigned_cells & cell_set
        n_multi_guide = sum(len(by_cell[cell]) > 1 for cell in known_assignments)
        targets = {_target_for_guide(guide) for guide in by_guide}
        if "NTC" not in targets:
            report.add_error(
                "missing_non_targeting_control",
                "No non-targeting control guide was found",
                context=context,
            )

        targets_by_context[context] = targets
        genes_by_context[context] = set(genes)
        condition_summaries[context] = {
            "sample_accession": files.sample_accession,
            "cells": n_cells,
            "genes": n_genes,
            "nonzero_values": n_nonzero,
            "guides": len(by_guide),
            "target_genes": len(targets - {"NTC"}),
            "assigned_matrix_cells": len(known_assignments),
            "unassigned_matrix_cells": len(cell_set - assigned_cells),
            "multi_guide_matrix_cells": n_multi_guide,
            "assignment_barcodes_without_expression": len(unknown_assignment_cells),
        }

    if len(targets_by_context) == len(CONDITION_FILES):
        shared_targets = set.intersection(*targets_by_context.values())
        if any(targets != shared_targets for targets in targets_by_context.values()):
            report.add_warning(
                "target_set_differs_by_context",
                "Perturbation target sets differ between biological contexts",
                shared_targets=len(shared_targets - {"NTC"}),
            )
        condition_summaries["shared_target_genes"] = len(shared_targets - {"NTC"})
        condition_summaries["shared_expression_genes"] = len(
            set.intersection(*genes_by_context.values())
        )

    report.summary["conditions"] = condition_summaries
    report.summary["supported_ood_dimensions"] = ["unseen_perturbation", "lps_context"]
    report.summary["unsupported_ood_dimensions"] = ["unseen_donor", "unseen_cell_type"]
    return report


def load_dixit_bmdc(root: str | Path, context: DixitCondition) -> AnnData:
    """Load one released BMDC condition as cells-by-genes sparse AnnData."""

    import anndata as ad
    import numpy as np
    import pandas as pd
    from scipy.io import mmread

    if context not in CONDITION_FILES:
        choices = ", ".join(CONDITION_FILES)
        raise ValueError(f"Unknown context {context!r}; expected one of: {choices}")

    root = Path(root)
    report = inspect_dixit_bmdc(root)
    report.raise_for_errors()
    files = CONDITION_FILES[context]
    cells = _read_index(root / files.cells)
    genes = _read_index(root / files.genes)
    by_cell, _ = _read_assignments(root / files.assignments)

    with gzip.open(root / files.matrix, "rb") as handle:
        matrix = mmread(handle).tocsr().transpose().tocsr().astype(np.float32)

    cell_set = set(cells)
    by_cell = {cell: guides for cell, guides in by_cell.items() if cell in cell_set}
    guide_lists = [by_cell.get(cell, []) for cell in cells]
    target_lists = [
        sorted({_target_for_guide(guide) for guide in guides if "NTC" not in guide})
        for guides in guide_lists
    ]
    obs = pd.DataFrame(
        {
            "sample_accession": files.sample_accession,
            "context": context,
            "guide_ids": ["|".join(guides) for guides in guide_lists],
            "target_genes": ["|".join(targets) for targets in target_lists],
            "n_guides": [len(guides) for guides in guide_lists],
            "n_targets": [len(targets) for targets in target_lists],
            "assignment_class": [_assignment_class(guides) for guides in guide_lists],
            "is_control": [_assignment_class(guides) == "non_targeting_control" for guides in guide_lists],
        },
        index=pd.Index(cells, name="cell_id"),
    )
    parsed_genes = [_parse_gene(gene) for gene in genes]
    var = pd.DataFrame(
        {
            "ensembl_gene_id": [gene_id for gene_id, _ in parsed_genes],
            "gene_symbol": [symbol for _, symbol in parsed_genes],
        },
        index=pd.Index(genes, name="feature_id"),
    )
    data = ad.AnnData(X=matrix, obs=obs, var=var)
    data.uns["dataset"] = "dixit_2016_bmdc"
    data.uns["series_accession"] = "GSE90063"
    data.uns["validation"] = report.to_dict()
    return data
