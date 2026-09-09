"""Validate sandbox review records before report use."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

ReviewDecision = Literal["pending", "approved", "rejected", "needs_revision"]


class ReviewError(ValueError):
    """Raised when a review record cannot authorize an artifact."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_review(
    review_path: str | Path,
    *,
    artifact_path: str | Path,
    expected_run_id: str,
    require_approval: bool = True,
) -> dict[str, object]:
    """Validate a review record and optionally require human approval."""

    review_file = Path(review_path)
    artifact_file = Path(artifact_path)
    try:
        review = json.loads(review_file.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewError(f"Unable to read review record: {error}") from error
    if not isinstance(review, dict):
        raise ReviewError("Review record must be a JSON object")
    if review.get("run_id") != expected_run_id:
        raise ReviewError("Review run_id does not match the expected benchmark run")
    if review.get("artifact_sha256") != _sha256(artifact_file):
        raise ReviewError("Review artifact_sha256 does not match the artifact")
    decision = review.get("decision")
    if decision not in {"pending", "approved", "rejected", "needs_revision"}:
        raise ReviewError("Review decision is invalid")
    if require_approval:
        if decision != "approved":
            raise ReviewError(f"Artifact review decision is {decision!r}, not approved")
        if not str(review.get("reviewer", "")).strip():
            raise ReviewError("Approved reviews require a reviewer")
    return review
