"""Structured validation results for dataset ingestion."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ValidationIssue:
    """One actionable validation finding."""

    severity: Literal["error", "warning"]
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Validation summary that keeps errors separate from documented limitations."""

    dataset: str
    summary: dict[str, Any] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add_error(self, code: str, message: str, **context: Any) -> None:
        self.issues.append(ValidationIssue("error", code, message, context))

    def add_warning(self, code: str, message: str, **context: Any) -> None:
        self.issues.append(ValidationIssue("warning", code, message, context))

    def raise_for_errors(self) -> None:
        errors = [issue for issue in self.issues if issue.severity == "error"]
        if errors:
            details = "; ".join(f"{issue.code}: {issue.message}" for issue in errors)
            raise ValueError(f"Dataset validation failed: {details}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "valid": self.valid,
            "summary": self.summary,
            "issues": [asdict(issue) for issue in self.issues],
        }
