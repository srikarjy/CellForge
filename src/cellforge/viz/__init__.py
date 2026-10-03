"""Question-driven, optional Plotly visualizations for CellForge artifacts."""

from cellforge.viz.candidates import candidate_evidence_card
from cellforge.viz.contradictions import contradiction_matrix
from cellforge.viz.model_trust import model_failure_analysis, model_reality_check
from cellforge.viz.provenance import provenance_dag
from cellforge.viz.response import experimental_landscape, response_explorer
from cellforge.viz.evidence import evidence_graph
from cellforge.viz.trust_map import perturbation_trust_map

__all__ = [
    "candidate_evidence_card",
    "contradiction_matrix",
    "model_reality_check",
    "model_failure_analysis",
    "perturbation_trust_map",
    "provenance_dag",
    "experimental_landscape",
    "response_explorer",
    "evidence_graph",
]
