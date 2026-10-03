# CellForge decision package

CellForge's first product output is a reviewable decision package, not an autonomous recommendation.
It binds a scientific question to connector provenance, dataset/model results, candidate interventions,
limitations, and a human review state.

```text
question + scope → multi-connector workflow → evidence → candidates → predictions → human review
```

`cellforge.decision.DecisionPackage` enforces unique IDs, rejects candidates that cite unknown evidence,
requires finite prediction metrics, and requires a reviewer before approval. Its canonical JSON
representation has a SHA-256 identity. Model predictions remain typed as model evidence; they are never
silently promoted to measured biological evidence.

Candidate triage is provided by `cellforge.prioritize`. Its explicit weights and
component values are retained in each candidate; the resulting order is a review
queue, not a claim of experimental efficacy.

The first end-to-end workflow targets perturbation prioritization in immune cells. A package may say
“needs review,” “rejected,” or “insufficient evidence”; no candidate is automatically authorized for
laboratory work.
