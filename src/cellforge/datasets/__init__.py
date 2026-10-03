"""Dataset ingestion interfaces."""

from cellforge.datasets.dixit_2016_bmdc import (
    CONDITION_FILES,
    DixitCondition,
    inspect_dixit_bmdc,
    load_dixit_bmdc,
)
from cellforge.datasets.norman_2019 import (
    NORMAN_ACCESSION,
    inspect_norman,
    load_norman_2019,
    load_norman_2019_from_pertpy,
    normalize_norman,
    prepare_norman_subset,
)

__all__ = [
    "CONDITION_FILES",
    "DixitCondition",
    "inspect_dixit_bmdc",
    "load_dixit_bmdc",
    "NORMAN_ACCESSION",
    "inspect_norman",
    "load_norman_2019",
    "load_norman_2019_from_pertpy",
    "normalize_norman",
    "prepare_norman_subset",
]
