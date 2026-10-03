# Transparent candidate prioritization

CellForge's candidate order is a triage aid for human review, not an efficacy
probability. `cellforge.prioritize` keeps the components visible:

- measurement reliability;
- response strength;
- model trust against declared baselines;
- independent evidence support;
- contradiction penalty and missing evidence.

Weights and contradiction limits are explicit in `PriorityConfig` and should
be stored with the run. A large model prediction cannot compensate for an
`UNRELIABLE` or `INSUFFICIENT_DATA` measurement by default. The resulting
`Candidate` preserves its components, limitations, and contradiction IDs inside
the existing `DecisionPackage` contract.
