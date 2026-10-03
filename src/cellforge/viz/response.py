from collections.abc import Sequence

import numpy as np

from cellforge.measure import PerturbationResponse
from cellforge.viz._optional import plotly


def response_explorer(response: PerturbationResponse):
    """Show the ranked changed genes for one measured perturbation."""
    go = plotly()
    pairs = sorted(zip(response.top_genes, response.delta), key=lambda item: -abs(item[1]))
    fig = go.Figure(go.Bar(x=[value for _, value in pairs], y=[gene for gene, _ in pairs], orientation="h"))
    fig.update_layout(title=f"Response Explorer: {response.perturbation}", xaxis_title="Mean expression delta", yaxis_title="Gene")
    return fig


def experimental_landscape(matrix: np.ndarray, labels: Sequence[str]):
    """Return a deterministic 2-D PCA-like view for an already prepared matrix.

    Dimensionality reduction is deliberately not performed in the UI; callers pass
    a validated embedding (for example from Scanpy) and its real labels.
    """
    go = plotly()
    if matrix.ndim != 2 or matrix.shape[1] < 2 or len(labels) != matrix.shape[0]:
        raise ValueError("matrix must be n-by-2-or-more and labels must match rows")
    fig = go.Figure(go.Scatter(x=matrix[:, 0], y=matrix[:, 1], mode="markers", text=list(labels), hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(title="Experimental Landscape", xaxis_title="Embedding 1", yaxis_title="Embedding 2")
    return fig
