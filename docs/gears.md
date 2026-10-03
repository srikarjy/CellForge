# GEARS integration

CellForge chooses GEARS as its single advanced-model adapter for the Norman
milestone. The official implementation targets single- and multi-gene
perturbation response prediction and documents a Norman workflow. CPA was not
selected because its public repository is archived and its primary workflow is
more naturally organized around compositional drug/dose covariates.

The adapter is optional because GEARS requires `cell-gears`, PyTorch Geometric,
and platform-specific wheels. Install those in a separate model environment;
the core test environment does not train it.

```bash
cellforge run-model \
  --dataset /path/to/normalized_norman.h5ad \
  --model gears \
  --config configs/norman_gears.json \
  --output artifacts/norman-gears
```

The command first creates the deterministic CellForge unseen-perturbation split,
then evaluates control-mean, training-mean, embedding-ridge, and GEARS on the
same held-out perturbations. It writes the split manifest and JSON metrics.
GEARS is not considered successful merely because training completes: its
per-perturbation scores must beat the declared baselines before trust can be
elevated.

## Compute expectations

Data preparation is CPU-friendly but can be memory-heavy for a full Norman
matrix. A small, documented subset is appropriate for a MacBook Air M2. Full
GEARS training is better suited to a Colab Pro GPU; CPU mode is provided for a
small smoke/demo run and is not presented as a performance benchmark. Runtime,
memory, and metrics must be recorded in the run artifact rather than inferred.
