# Data policy

No dataset is selected, downloaded, or processed in Stage 1. Phase 1 will document one public source, its provenance, access/license conditions, release or snapshot, identifiers, controls, metadata, and limitations before implementing ingestion.

| Category | Intended location | Version-control policy |
| --- | --- | --- |
| External source data | Upstream repository or archive | Commit provenance and retrieval references, not upstream payloads |
| Downloaded raw data | `data/raw/` or `data/external/` | Ignore payloads; preserve versions and checksums in tracked documentation/manifests |
| Processed data | `data/processed/` | Ignore derived arrays; retain transformation configurations and provenance |
| Cached artifacts | `data/cache/` or `.cache/` | Ignore; rebuild from fingerprinted inputs |
| Small test fixtures | `tests/fixtures/` when needed | Track small, documented, redistributable or synthetic fixtures explicitly |

Do not blindly commit large single-cell matrices, AnnData files, checkpoints, or predictions. Keep shareable manifests and source metadata outside ignored payload directories. Review file size, redistribution terms, and privacy before adding a fixture; the fixture exception is not permission to commit full datasets. Do not store credentials or restricted participant data in Git.

Download procedures and deterministic preprocessing will be implemented later. Cached preprocessing must eventually bind source identity, configuration, fitted training state, and software version to prevent stale reuse.
