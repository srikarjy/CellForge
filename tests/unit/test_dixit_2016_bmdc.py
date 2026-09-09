import csv
import gzip
from pathlib import Path

import pytest

from cellforge.datasets.dixit_2016_bmdc import CONDITION_FILES, inspect_dixit_bmdc


def _write_index(path: Path, values: list[str]) -> None:
    with gzip.open(path, "wt", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["", "0"])
        writer.writerows(enumerate(values))


def _write_condition(root: Path, context: str) -> None:
    files = CONDITION_FILES[context]  # type: ignore[index]
    with gzip.open(root / files.matrix, "wt") as handle:
        handle.write("%%MatrixMarket matrix coordinate real general\n%\n2 3 3\n")
        handle.write("1 1 2\n1 3 1\n2 2 4\n")
    cells = [f"cell_{context}_{index}" for index in range(3)]
    _write_index(root / files.cells, cells)
    _write_index(root / files.genes, ["ENSMUSG00000000001_GeneA", "ENSMUSG00000000002_GeneB"])
    with gzip.open(root / files.assignments, "wt", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["m_GeneA_1", f"{cells[0]}, {cells[1]}"])
        writer.writerow(["m_MouseNTC_100_A_67005", cells[2]])


def test_inspection_accepts_consistent_fixture(tmp_path: Path) -> None:
    for context in CONDITION_FILES:
        _write_condition(tmp_path, context)

    report = inspect_dixit_bmdc(tmp_path)

    assert report.valid
    assert report.summary["conditions"]["shared_target_genes"] == 1
    assert report.summary["supported_ood_dimensions"] == ["unseen_perturbation", "lps_context"]


def test_inspection_reports_missing_files(tmp_path: Path) -> None:
    report = inspect_dixit_bmdc(tmp_path)

    assert not report.valid
    with pytest.raises(ValueError, match="missing_source_files"):
        report.raise_for_errors()
