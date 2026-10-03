"""Explicit disagreement detection for scientific review."""

from cellforge.contradictions.rules import Contradiction, ContradictionSeverity, find_evidence_contradictions, find_model_contradictions

__all__ = ["Contradiction", "ContradictionSeverity", "find_evidence_contradictions", "find_model_contradictions"]
