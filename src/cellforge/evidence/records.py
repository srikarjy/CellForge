"""Provider-neutral evidence normalization; connectors remain responsible for retrieval."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class EvidenceType(str, Enum):
    LITERATURE = "literature"
    PATHWAY = "pathway"
    DEPENDENCY = "dependency"
    DATASET = "dataset"
    STRUCTURE = "structure"


class EvidenceDirection(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EvidenceRecord:
    source: str
    source_id: str
    target: str
    claim: str
    evidence_type: EvidenceType
    direction: EvidenceDirection
    payload_hash: str
    query: str = ""
    retrieved_at: str | None = None
    url: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("source", "source_id", "target", "claim", "payload_hash"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"Evidence {name} is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_evidence(
    *,
    source: str,
    source_id: str,
    target: str,
    claim: str,
    evidence_type: EvidenceType,
    direction: EvidenceDirection,
    payload: Mapping[str, Any] | list[Any] | str,
    query: str = "",
    retrieved_at: str | None = None,
    url: str | None = None,
    limitations: tuple[str, ...] = (),
) -> EvidenceRecord:
    """Canonicalize a provider payload and attach its content hash."""

    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    payload_hash = hashlib.sha256(encoded).hexdigest()
    return EvidenceRecord(source, source_id, target, claim, evidence_type, direction, payload_hash, query, retrieved_at, url, limitations)
