"""Optional Streamlit artifact viewer; scientific computation stays in CellForge modules."""

from __future__ import annotations

import json
from pathlib import Path


def render(package_path: str | Path) -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install CellForge's optional 'app' dependencies") from exc
    path = Path(package_path)
    artifact_dir = path if path.is_dir() else path.parent
    package_file = artifact_dir / "decision" / "package.json" if path.is_dir() else path
    payload = json.loads(package_file.read_text())
    run_manifest = {}
    if (artifact_dir / "run_manifest.json").is_file():
        run_manifest = json.loads((artifact_dir / "run_manifest.json").read_text())
    st.set_page_config(page_title="CellForge", layout="wide")
    st.title("CellForge decision workspace")
    st.caption("Reliability-aware review of perturbation experiment evidence")
    st.info(
        f"Dataset: {'REAL' if run_manifest else 'artifact'}  |  "
        f"GEARS: {'REAL' if run_manifest.get('gears_model') else 'not recorded'}  |  "
        f"External evidence: {run_manifest.get('external_evidence_mode', 'unknown').upper()}"
    )
    pages = ["Run Overview", "Experiment", "Reliability", "Model Trust", "Candidates", "Evidence", "Contradictions", "Provenance", "Decision Package"]
    page = st.sidebar.selectbox("View", pages)
    candidates = payload.get("candidates", [])
    if page == "Run Overview":
        st.metric("Candidates surfaced", len(candidates))
        st.write({"run_id": payload.get("run_id"), "status": payload.get("status"), "scope": payload.get("scope"), "dataset": run_manifest.get("dataset")})
    elif page == "Candidates":
        st.dataframe(candidates, use_container_width=True)
    elif page == "Decision Package":
        st.json(payload)
    elif page == "Model Trust" and (artifact_dir / "trust" / "model_trust.parquet").is_file():
        import pandas as pd
        st.dataframe(pd.read_parquet(artifact_dir / "trust" / "model_trust.parquet"), use_container_width=True)
    elif page == "Reliability" and (artifact_dir / "reliability" / "reliability.parquet").is_file():
        import pandas as pd
        st.dataframe(pd.read_parquet(artifact_dir / "reliability" / "reliability.parquet"), use_container_width=True)
    elif page == "Contradictions" and (artifact_dir / "contradictions" / "contradictions.json").is_file():
        st.json(json.loads((artifact_dir / "contradictions" / "contradictions.json").read_text()))
    else:
        st.info("This view consumes the corresponding artifact tables when present; no fabricated results are shown.")
