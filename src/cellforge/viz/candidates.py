from cellforge.decision import Candidate
from cellforge.viz._optional import plotly


def candidate_evidence_card(candidate: Candidate):
    """Return a compact, exportable table for one candidate review."""
    go = plotly()
    model_rows = [
        f"{item.model} / {item.split}: {item.value:.3f} (n={item.eligible_count})"
        for item in candidate.model_summaries or candidate.predictions
    ]
    rows = [
        ("Candidate", candidate.intervention),
        ("Measurement reliability", candidate.measurement_reliability or "unknown"),
        ("Model trust", candidate.model_trust or "unknown"),
        ("Model results", "; ".join(model_rows) or "not recorded"),
        ("Priority (triage only)", f"{candidate.priority_score:.3f}" if candidate.priority_score is not None else "unknown"),
        ("Why surfaced", candidate.rationale or "not recorded"),
        ("Limitations", "; ".join(candidate.limitations) or "none recorded"),
    ]
    fig = go.Figure(go.Table(header={"values": ["Field", "Value"]}, cells={"values": [[r[0] for r in rows], [r[1] for r in rows]]}))
    fig.update_layout(title="Candidate Evidence Card")
    return fig
