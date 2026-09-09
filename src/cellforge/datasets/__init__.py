"""Dataset ingestion interfaces."""

from cellforge.datasets.dixit_2016_bmdc import (
    CONDITION_FILES,
    DixitCondition,
    inspect_dixit_bmdc,
    load_dixit_bmdc,
)

__all__ = [
    "CONDITION_FILES",
    "DixitCondition",
    "inspect_dixit_bmdc",
    "load_dixit_bmdc",
]
