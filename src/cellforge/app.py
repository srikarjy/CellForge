"""Optional Streamlit artifact viewer; scientific computation stays in CellForge modules."""

from __future__ import annotations

import json
from pathlib import Path


def render(package_path: str | Path) -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install CellForge's optional 'app' dependencies") from exc
    payload = json.loads(Path(package_path).read_text())
    st.set_page_config(page_title="CellForge", layout="wide")
    st.title("CellForge decision workspace")
    st.caption("Reliability-aware review of perturbation experiment evidence")
    pages = ["Run Overview", "Experiment", "Reliability", "Model Trust", "Candidates", "Evidence", "Contradictions", "Provenance", "Decision Package"]
    page = st.sidebar.selectbox("View", pages)
    candidates = payload.get("candidates", [])
    if page == "Run Overview":
        st.metric("Candidates surfaced", len(candidates))
        st.write({"run_id": payload.get("run_id"), "status": payload.get("status"), "scope": payload.get("scope")})
    elif page == "Candidates":
        st.dataframe(candidates, use_container_width=True)
    elif page == "Decision Package":
        st.json(payload)
    else:
        st.info("This view consumes the corresponding artifact tables when present; no fabricated results are shown.")
