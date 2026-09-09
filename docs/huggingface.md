# Hugging Face integration

Hugging Face is an optional artifact and model source for CellForge. It can host model checkpoints, dataset snapshots, Spaces, and future inference endpoints. It does not replace the benchmark's dataset validation, split definitions, biological metrics, or human review policy.

## Authentication

Use the Hugging Face CLI or an environment variable supplied by the user:

```text
hf auth login
```

or:

```text
HF_TOKEN=... hf download <namespace>/<repository> --revision <commit-or-tag>
```

Never place `HF_TOKEN` in a committed file, configuration example, review record, benchmark manifest, or command history copied into documentation. The repository should reference the token by environment variable only. Do not print token values in logs.

## Reproducible downloads

Every future model or dataset download must record:

- repository ID and type (`model`, `dataset`, or `space`)
- exact revision or commit hash
- selected file paths and local checksums
- license and access status
- download timestamp
- software/runtime requirements
- whether the artifact is a model input, checkpoint, or derived output

Use the modern `hf` CLI, not the deprecated `huggingface-cli` command. Keep the Hub cache and downloaded payloads outside version control. Large checkpoints belong in external storage or the local cache; a small manifest with checksums and retrieval instructions can be committed.

## CellForge model boundary

Hugging Face model availability is not evidence that a model is suitable for single-cell perturbation prediction. An adapter must establish compatible inputs, perturbation semantics, outputs, evaluation scale, and information access. Compare the model with the same dataset version, split membership, baseline contract, and metrics as other participants.

The first Hugging Face integration should be read-only model retrieval or an explicitly pinned inference artifact. Do not upload private data, review records, or biological source files to a Hub repository without a separate user decision and a documented redistribution policy.

## Sandbox use

The local artifact sandbox may later load a pinned model output or structure artifact downloaded from Hugging Face. The browser sandbox must continue to process files locally and must not receive the user's Hugging Face token. Model execution should happen in a separate adapter or job environment, with predictions passed to the deterministic checker and human review loop as ordinary artifacts.

No specific Hugging Face model is selected yet. Selection depends on the benchmark task and should be recorded in the model adapter contract before download.
