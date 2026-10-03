from collections.abc import Sequence

import numpy as np

from cellforge.trust import ModelTrustRecord
from cellforge.viz._optional import plotly


def model_reality_check(records: Sequence[ModelTrustRecord]):
    """Compare advanced predictions with both declared baselines per perturbation."""
    go = plotly()
    names = [record.perturbation for record in records]
    fig = go.Figure()
    series = [("advanced", [r.advanced_score for r in records]), ("no-change", [r.control_score for r in records]), ("linear", [r.linear_score for r in records])]
    if any(np.isfinite(r.training_mean_score) for r in records):
        series.append(("training mean", [r.training_mean_score for r in records]))
    for label, values in series:
        fig.add_bar(name=label, x=names, y=values)
    fig.update_layout(barmode="group", title="Model Reality Check", xaxis_title="Perturbation", yaxis_title="Pearson delta score")
    return fig


def model_failure_analysis(records: Sequence[ModelTrustRecord]):
    """Rank cases where a baseline beats the advanced model."""
    go = plotly()
    failures = sorted(records, key=lambda item: item.advanced_score - max(item.control_score, item.linear_score))
    names = [item.perturbation for item in failures]
    gaps = [item.advanced_score - max(item.control_score, item.linear_score) for item in failures]
    fig = go.Figure(go.Bar(x=gaps, y=names, orientation="h", marker_color=["#c0392b" if gap < 0 else "#237a57" for gap in gaps]))
    fig.update_layout(title="Model Failure Analysis", xaxis_title="Advanced score minus best baseline", yaxis_title="Perturbation")
    return fig
