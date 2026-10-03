from collections.abc import Sequence

from cellforge.evidence import EvidenceRecord
from cellforge.viz._optional import plotly


def evidence_graph(records: Sequence[EvidenceRecord]):
    """Render only observed target-to-source evidence edges."""
    go = plotly()
    labels = sorted({record.target for record in records} | {record.source for record in records})
    index = {label: position for position, label in enumerate(labels)}
    edge_x, edge_y = [], []
    for record in records:
        edge_x.extend([index[record.target], index[record.source], None])
        edge_y.extend([0, 1, None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"color": "#9aa5b1"}, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[index[label] for label in labels], y=[0 if label in {r.target for r in records} else 1 for label in labels], mode="markers+text", text=labels, textposition="top center", hovertext=labels))
    fig.update_layout(title="Evidence Graph", xaxis={"visible": False}, yaxis={"visible": False}, showlegend=False)
    return fig
