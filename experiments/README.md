# Experiment organization

The future traceability chain is:

```text
configuration → run → predictions → metrics → report
```

An experiment groups a scientific question and its declared comparison settings. Each execution receives a distinct run ID and preserves resolved configuration, dataset/split references, model/checkpoint metadata, seeds, environment, status, and artifact references. Reruns must not overwrite earlier evidence.

A future run directory can keep a manifest and configuration snapshot beside references to predictions, metrics, logs, and reports. The exact directory and result schemas are deferred. Store large payloads in dedicated ignored artifact subdirectories or external storage; retain checksums and retrieval references in shareable manifests. Do not broadly ignore all experiment directories, since configurations and provenance belong in version control when publishable.

Generated payload conventions covered by `.gitignore` include `experiments/**/predictions/`, `artifacts/`, and `logs/`. Curated small result tables or reports may be committed intentionally once real experiments exist. There are no runs or fabricated results in Stage 1.
