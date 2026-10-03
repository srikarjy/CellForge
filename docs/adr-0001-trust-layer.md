# ADR-0001: Build CellForge as a reliability-aware trust layer

**Status:** Accepted  
**Date:** 2026-10-03  
**Deciders:** CellForge maintainers

## Context

Perturbation screens produce high-dimensional responses, but a large response
is not automatically a reliable or actionable result. Scientists also need to
know whether a predictive model adds information beyond simple baselines, what
independent biological sources support or contradict a candidate, and how the
conclusion can be reproduced later.

CellForge already contains dataset validation, biological splits, baselines,
evaluation, bounded connector execution, provenance, and human review gates.
The project must converge those components on one decision problem without
replacing mature perturbation-analysis libraries or becoming a generic agent.

## Decision

CellForge will be a reliability-aware trust layer between perturbation screens
and experimental decisions. The first workflow will use a pinned Norman 2019
CRISPRa Perturb-seq artifact and produce:

1. same-context perturbation response summaries;
2. explicit measurement reliability classes;
3. baseline-versus-model evaluation and per-perturbation trust records;
4. normalized external evidence and surfaced contradictions;
5. a deterministic, human-reviewed `DecisionPackage`.

The core scientific path remains a Python package. A future small artifact
viewer may inspect generated outputs, but scientific logic will not live in a
frontend. Connector count, model count, and chart count are not success
criteria.

## Options considered

### A. Reliability-aware trust layer (selected)

| Dimension | Assessment |
| --- | --- |
| Scientific usefulness | Directly addresses measurement and model uncertainty |
| Feasibility | Incremental with public data and existing code |
| Differentiation | Connects reliability, model trust, evidence, and provenance |
| Risk | Requires careful definitions and validation |

### B. Generic perturbation benchmark

| Dimension | Assessment |
| --- | --- |
| Scientific usefulness | Useful but increasingly crowded |
| Feasibility | High technically, weaker product distinction |
| Differentiation | Low without a trust/decision layer |
| Risk | Becomes another aggregate leaderboard |

### C. Autonomous AI scientist / multi-agent product

| Dimension | Assessment |
| --- | --- |
| Scientific usefulness | Unclear without validated decision boundaries |
| Feasibility | High integration complexity and evidence risk |
| Differentiation | Mostly orchestration rather than biology |
| Risk | Overclaims, unsafe autonomy, and connector sprawl |

## Consequences

- Reliability and model trust become first-class persisted objects.
- Every candidate retains limitations and evidence references.
- Baselines are mandatory before advanced-model interpretation.
- Norman is the first end-to-end dataset; Replogle is deferred until the
  smaller workflow is reliable.
- `pertpy` may provide mature analysis primitives, but CellForge owns the
  decision contract and provenance above them.
- Unsupported donor/cell-type claims remain explicitly unsupported.

## Action items

1. [x] Add a normalized Norman 2019 adapter.
2. [x] Add deterministic measurement summaries.
3. [x] Add configurable reliability classes.
4. [x] Add per-perturbation model-trust records.
5. [ ] Add fixture-backed evidence normalization and contradiction rules.
6. [ ] Add transparent prioritization and DecisionPackage integration.
7. [ ] Add one artifact viewer over real generated outputs.
