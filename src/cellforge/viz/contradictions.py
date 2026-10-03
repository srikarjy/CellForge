from collections.abc import Sequence

from cellforge.contradictions import Contradiction
from cellforge.viz._optional import plotly


def contradiction_matrix(records: Sequence[Contradiction]):
    """Show contradiction edges as a compact candidate-by-source matrix."""
    go = plotly()
    candidates = sorted({r.candidate for r in records})
    sources = sorted({source for r in records for source in (r.source_a, r.source_b)})
    values = [[1 if any(r.candidate == candidate and source in (r.source_a, r.source_b) for r in records) else 0 for source in sources] for candidate in candidates]
    fig = go.Figure(go.Heatmap(z=values, x=sources, y=candidates, colorscale=[[0, "#eef2f7"], [1, "#c0392b"]], zmin=0, zmax=1))
    fig.update_layout(title="Contradiction Matrix", xaxis_title="Evidence source", yaxis_title="Candidate")
    return fig
