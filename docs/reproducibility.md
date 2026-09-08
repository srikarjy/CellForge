# Future reproducibility contract

This is a conceptual contract, not an implemented or finalized manifest schema. A benchmark result will not be considered fully reproducible without enough information to reconstruct its data, prediction conditions, and evaluation.

## Information to preserve

| Field or concept | Required meaning |
| --- | --- |
| run_id | Unique identifier linking configuration and all artifacts |
| dataset_name, dataset_version | Source identity and pinned release/accession or documented snapshot |
| dataset_fingerprint | Digest identifying the actual evaluated data and relevant metadata |
| task | Prediction target, scale, gene universe, control policy, and evaluation unit |
| split, split_fingerprint | Split definition, exact membership, and identity checks |
| seed | All relevant random seeds and how they are assigned |
| preprocessing_configuration | Resolved transformations, fitted state references, and fingerprint |
| model, model_version | Model identity and version |
| checkpoint | Checkpoint origin, identifier, and hash where available |
| adapter_version | Adapter code version, including repository revision |
| model_configuration | Fitting, tuning, and inference settings and input access policy |
| metric_configuration | Metric definitions, grouping, thresholds, and aggregation |
| software_environment | Source revision, dependencies, platform, and relevant hardware/runtime details |
| timestamp | Execution time with timezone |
| result_artifacts | Predictions, metrics, logs, reports, and their paths/checksums |

## Deterministic seeds and splits

Record seeds for split generation, fitting, sampling, and framework randomness. Preserve exact cell/condition membership, counts, distributions, and overlap checks. The same dataset and resolved split configuration must reconstruct the same split. Seeds alone do not guarantee deterministic accelerator execution; record known nondeterminism and distinguish exact reproduction from tolerance-based reproduction.

## Immutable run manifests

Capture resolved settings rather than relying on mutable defaults or filenames. Finalized manifests and artifacts must not be silently overwritten; reruns receive distinct identities linked to the same experiment configuration. Record completion/failure status and partial outputs. A manifest must include software revision and relevant uncommitted changes or identify that the run came from a clean checkout. Exclude secrets and credentials from environment capture.

## Fingerprinting and cached preprocessing

A future cache key will include data fingerprints, canonical preprocessing configuration, code/software versions, and split membership for training-fitted transformations. Persist fitted transformation state and its identity. A changed input, training split, or transformation invalidates the corresponding cache. Validate cached artifact integrity before reuse and never use a shared fitted transform that crosses a holdout boundary.

Fingerprint rules must specify exactly which bytes or canonical contents are hashed. Source versions alone are insufficient when upstream files can change. No cache or hashing implementation exists in Stage 1.

## Environment and model capture

Record resolved dependencies, Python version, operating system, relevant hardware and accelerator runtime, model package versions, checkpoint identity, adapter version, and inference configuration. Document unavailable hashes or opaque hosted resources as reproducibility limitations. Keep environment snapshots with runs once execution exists.

## Raw predictions and derived metrics

Persist predictions with cell or condition identifiers, gene identifiers, expression scale, and the references required to align observations and controls. Metrics must be recomputable from those predictions, the pinned evaluation data, and metric configuration without rerunning inference. Reports must consume preserved results and expose exclusions and failed runs.

Machine-readable results may conceptually contain run_id, dataset, task, split, model, seed, metric, value, and metadata. Their final schema is intentionally deferred. Do not commit large prediction arrays merely to retain provenance: store checksummed artifacts externally when appropriate and keep shareable manifests and retrieval references under version control.

## Delivery sequence

The first executable benchmark must preserve basic configuration, split membership, predictions, and a run manifest before any comparison is presented as reproducible. Roadmap Phase 10 hardens this foundation with robust fingerprints, cache handling, and artifact management; it does not defer provenance until after publication.
