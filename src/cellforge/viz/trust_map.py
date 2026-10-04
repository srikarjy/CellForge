from collections.abc import Mapping, Sequence

from cellforge.measure import PerturbationResponse
from cellforge.reliability import PerturbationReliability
from cellforge.trust import ModelTrustRecord
from cellforge.viz._optional import plotly


def perturbation_trust_map(
    responses: Sequence[PerturbationResponse],
    reliability: Sequence[PerturbationReliability],
    model_trust: Mapping[str, ModelTrustRecord] | None = None,
):
    """Return the signature response-strength-versus-reliability figure."""
    go = plotly()
    rel = {item.perturbation: item for item in reliability}
    trust = model_trust or {}
    rows = [item for item in responses if item.perturbation in rel]
    colors = {"SPECIFIC": "#237a57", "SHARED": "#d68910", "UNRELIABLE": "#c0392b", "INSUFFICIENT_DATA": "#7f8c8d"}
    fig = go.Figure(
        go.Scatter(
            x=[rel[item.perturbation].signal_to_noise for item in rows],
            y=[item.effect_magnitude for item in rows],
            mode="markers",
            marker={"size": [max(8, min(36, item.cells / 5)) for item in rows], "color": [colors[rel[item.perturbation].classification.value] for item in rows]},
            text=[item.perturbation for item in rows],
            customdata=[[item.cells, rel[item.perturbation].classification.value, rel[item.perturbation].method, rel[item.perturbation].median_split_correlation, rel[item.perturbation].shared_cosine, trust.get(item.perturbation).trust_status.value if item.perturbation in trust else "unknown"] for item in rows],
            hovertemplate="%{text}<br>reliability statistic=%{x:.3g}<br>Effect=%{y:.3g}<br>cells=%{customdata[0]}<br>class=%{customdata[1]}<br>method=%{customdata[2]}<br>median split r=%{customdata[3]:.3g}<br>shared cosine=%{customdata[4]:.3g}<br>model trust=%{customdata[5]}<extra></extra>",
        )
    )
    fig.update_layout(title="Perturbation Trust Map", xaxis_title="Reliability statistic (method-specific)", yaxis_title="Response magnitude")
    return fig
