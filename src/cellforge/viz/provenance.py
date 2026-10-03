from cellforge.decision import DecisionPackage
from cellforge.viz._optional import plotly


def provenance_dag(package: DecisionPackage):
    """Render the package's recorded provenance chain; no inferred edges are added."""
    go = plotly()
    names = ["dataset", "measurement", "model/split", "workflow", "DecisionPackage"]
    values = [dict(package.provenance).get(key, "") for key in ("dataset_fingerprint", "measurement_artifact_sha256", "split_sha256", "workflow_manifest_sha256", "workflow_manifest_sha256")]
    fig = go.Figure(go.Table(header={"values": ["Stage", "Identifier / hash"]}, cells={"values": [names, values]}))
    fig.update_layout(title="Provenance DAG (recorded identifiers)")
    return fig
