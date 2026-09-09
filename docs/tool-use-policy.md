# CellForge tool-use policy

This policy defines which external tools and computational actions may be used by CellForge integrations. It is a reviewable contract for future enforcement; the repository does not yet implement a general policy engine.

## Core rules

1. Tools are allowlisted by task. A tool may not be called merely because it is available.
2. User-selected files are treated as untrusted input and are processed within bounded resource limits.
3. No tool may upload user data, credentials, private datasets, or review records without an explicit user decision for that destination.
4. Every model or external analysis must record its version, input artifact hash, configuration, and output artifact hash.
5. Automated checks may recommend or block a review, but only a human reviewer can approve a scientific artifact for benchmark use.
6. Tool failure, timeout, truncation, or unsupported input is recorded as a failure or needs-review state; it must not be silently retried without limits.

## Allowlist

| Tool family | Permitted use | Default boundary |
| --- | --- | --- |
| Cellxgene/Census | Discover public datasets and retrieve declared AnnData subsets | Public sources only; record collection/dataset ID and revision |
| GEO/NCBI | Retrieve and verify public source metadata and declared supplementary files | Accession-scoped requests; preserve source URLs and checksums |
| Sequence viewer | Inspect FASTA/FASTQ and bounded annotations | Local files; no implicit external search or upload |
| Structure viewer | Render and inspect PDB/mmCIF and bounded related artifacts | Local files or explicitly requested public accession |
| Hugging Face Hub | Download pinned public or user-authorized models/datasets | Exact repository revision; token stays outside the browser and Git |
| Evo 2 | DNA sequence generation, embeddings, or forward analysis where task-compatible | Separate sequence task; never silently treat output as RNA perturbation prediction |
| PhysicsNeMo/MD backend | Explicit physics-informed or molecular-dynamics experiment | Requires structure, force-field/model choice, bounded trajectory, and review |
| Deterministic CellForge validators | Schema, identifier, provenance, and artifact checks | No model-generated claims; outputs are findings with evidence |

Unlisted tools, arbitrary URLs, cloud databases, workflow engines, and autonomous agents require a separate design review. A tool's presence in the environment is not authorization to invoke it.

## Resource limits

The initial local sandbox should enforce these defaults:

- maximum browser artifact size: 25 MiB;
- maximum structure render: 250,000 atoms and 8,000 residues;
- maximum FASTA records: 10,000;
- maximum sequence length per record: 10 million symbols;
- maximum review JSON size: 5 MiB;
- maximum local analysis runtime: 5 minutes per request;
- maximum concurrent analyses: 1 in the browser and a declared bounded count in batch jobs;
- maximum retry count: 2 for transient tool failures, with backoff;
- maximum exported movie/render duration: 60 seconds unless a human explicitly requests a larger bound;
- no unbounded trajectory, tensor, prediction, or search-result materialization into chat.

Scientific workloads may use larger limits in a controlled batch environment, but the run manifest must record the override, reason, resource allocation, and reviewer authorization.

## Network and credentials

The browser sandbox is local-only and must not receive tokens. Network access belongs in a separate retrieval or model adapter. Restrict outbound requests to the declared provider and exact resource needed for the task. Pin revisions where the provider supports them. Keep `HF_TOKEN`, NVIDIA keys, and other credentials in environment or OS credential storage; never write them to source, manifests, logs, exported review JSON, or screenshots.

Downloaded data and checkpoints remain outside Git by default. Preserve small provenance manifests, checksums, licenses, and retrieval instructions instead of large payloads.

## Human approval gates

Require a human decision before:

- marking an artifact approved for benchmark use;
- accepting a model output as biologically interpretable;
- publishing a report or dataset-derived artifact;
- uploading anything to Hugging Face, Cellxgene, or another external service;
- increasing resource limits or enabling a new tool family;
- treating an Evo or PhysicsNeMo result as evidence about cellular perturbation response.

The review record should include reviewer identity, decision, notes for rejected or revised artifacts, checker version, input hash, output hashes, and timestamp. A pending or failed check cannot be converted to approval by a default value.

## Abuse and failure handling

Stop processing when an input exceeds a limit, a parser detects malformed content, a tool requests an undeclared destination, or a model returns an incompatible output. Surface the exact reason and preserve a bounded diagnostic. Do not use repeated retries to bypass a limit. Do not interpret a timeout, empty result, or partial response as a successful biological result.

## Enforcement roadmap

Phase 1 records these rules in documentation and keeps the browser sandbox bounded. A future enforcement layer should validate a resolved tool request against this policy before execution, emit an auditable decision, and attach the policy version to the run manifest. Enforcement should be tested with oversized files, malformed structures, invalid URLs, missing credentials, incompatible model outputs, repeated failures, and attempted external uploads.
