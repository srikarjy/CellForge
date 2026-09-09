import hashlib
import json
from pathlib import Path

import pytest

from cellforge.artifacts import ReviewError, validate_review


def _write_review(path: Path, artifact: Path, decision: str = "approved") -> None:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    path.write_text(json.dumps({"run_id": "run-1", "artifact_sha256": digest, "decision": decision, "reviewer": "Ada"}))


def test_approved_matching_review_is_accepted(tmp_path: Path) -> None:
    artifact = tmp_path / "prediction.json"
    artifact.write_text("{}")
    review = tmp_path / "review.json"
    _write_review(review, artifact)
    assert validate_review(review, artifact_path=artifact, expected_run_id="run-1")["decision"] == "approved"


@pytest.mark.parametrize("decision", ["pending", "rejected", "needs_revision"])
def test_non_approved_review_is_blocked(tmp_path: Path, decision: str) -> None:
    artifact = tmp_path / "prediction.json"
    artifact.write_text("{}")
    review = tmp_path / "review.json"
    _write_review(review, artifact, decision)
    with pytest.raises(ReviewError, match="not approved"):
        validate_review(review, artifact_path=artifact, expected_run_id="run-1")


def test_hash_mismatch_is_blocked(tmp_path: Path) -> None:
    artifact = tmp_path / "prediction.json"
    artifact.write_text("{}")
    review = tmp_path / "review.json"
    _write_review(review, artifact)
    artifact.write_text('{"changed": true}')
    with pytest.raises(ReviewError, match="sha256"):
        validate_review(review, artifact_path=artifact, expected_run_id="run-1")
