def plotly():
    try:
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover - exercised in minimal installs
        raise RuntimeError("Install CellForge's optional 'viz' dependencies to use plotting") from exc
    return go
