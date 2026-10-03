#!/usr/bin/env bash
set -euo pipefail

# Run this in a fresh Colab runtime (or a dedicated local venv). GEARS/PyG are
# intentionally not part of CellForge's core environment because their wheels
# are coupled to the selected PyTorch/CUDA runtime.
python -m pip install --upgrade pip
python -m pip install "cell-gears==0.1.2" "torch-geometric>=2.5,<3" \
  "scanpy>=1.10,<1.12" "anndata>=0.10,<0.13" "numpy>=1.26,<2" \
  "pandas>=2.1,<2.3" "scikit-learn>=1.3" "networkx>=3" "dcor>=0.6"

# GEARS uses this official graph asset during PertData initialization. Keep it
# outside the repository and point --gears-data-dir at this directory.
export CELLFORGE_GEARS_DATA_DIR="${CELLFORGE_GEARS_DATA_DIR:-$PWD/.cellforge-gears-data}"
mkdir -p "$CELLFORGE_GEARS_DATA_DIR"
if [ ! -f "$CELLFORGE_GEARS_DATA_DIR/gene2go_all.pkl" ]; then
  curl -L --fail --silent --show-error \
    -o "$CELLFORGE_GEARS_DATA_DIR/gene2go_all.pkl" \
    https://dataverse.harvard.edu/api/access/datafile/6153417
fi
echo "CELLFORGE_GEARS_DATA_DIR=$CELLFORGE_GEARS_DATA_DIR"

python - <<'PY'
import importlib.metadata as metadata
import platform
import sys

for name in ("torch", "torch-geometric", "cell-gears", "numpy", "pandas", "scanpy", "anndata"):
    try:
        print(f"{name}=={metadata.version(name)}")
    except metadata.PackageNotFoundError:
        print(f"{name}==NOT_INSTALLED")
print(f"python=={platform.python_version()}")
print(f"platform=={platform.platform()}")
try:
    import torch
    print(f"cuda=={torch.version.cuda or 'cpu'}")
    print(f"cuda_available=={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"gpu=={torch.cuda.get_device_name(0)}")
except ImportError:
    print("torch==NOT_INSTALLED")
PY
