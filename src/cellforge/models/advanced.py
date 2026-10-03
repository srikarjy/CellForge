"""Adapters for one optional advanced model: GEARS.

The adapter owns only the translation boundary. CellForge still owns splits,
metrics, trust, provenance, and downstream decisions. GEARS is intentionally an
optional dependency because PyG/CUDA wheels are platform-specific.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import numpy as np

from cellforge.evaluation.contract import Predictions
from cellforge.splits import SplitColumns, dataset_fingerprint


@dataclass(frozen=True)
class ModelIdentity:
    name: str
    version: str
    package: str
    config: dict[str, Any] = field(default_factory=dict)
    seed: int = 0

    @property
    def config_sha256(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


class GEARSBackend(Protocol):
    """Small backend seam used by both the real package and CPU test doubles."""

    version: str

    def fit(self, train: Any, columns: SplitColumns, config: dict[str, Any], seed: int) -> None: ...

    def predict(self, perturbations: Sequence[str], genes: Sequence[str]) -> np.ndarray: ...


class _PackageGEARSBackend:
    """Thin best-effort bridge to the official ``cell-gears`` API.

    The package's graph/PyG setup is deliberately not imported until a real run
    is requested. This keeps normal CellForge installation and CI lightweight.
    """

    version = "unknown"

    def __init__(self, data_dir: str, model_config: dict[str, Any]) -> None:
        try:
            from gears import GEARS, PertData
        except ImportError as exc:  # pragma: no cover - depends on optional environment
            raise RuntimeError(
                "GEARS requires the optional model environment (cell-gears + a compatible PyG wheel)"
            ) from exc
        self._GEARS = GEARS
        self._PertData = PertData
        self._data_dir = data_dir
        self._model_config = dict(model_config)
        try:
            import gears as gears_package

            self.version = str(getattr(gears_package, "__version__", "unknown"))
        except Exception:  # pragma: no cover - defensive metadata only
            pass

    def fit(self, train: Any, columns: SplitColumns, config: dict[str, Any], seed: int) -> None:
        import anndata as ad

        data = train.copy()
        data.obs["condition"] = data.obs[columns.perturbation].astype(str)
        data.obs["cell_type"] = data.obs[columns.context].astype(str) if columns.context in data.obs else "default"
        data.var["gene_name"] = data.var_names.astype(str)
        self._pert_data = self._PertData(self._data_dir)
        self._pert_data.new_data_process(dataset_name="cellforge_train", adata=ad.AnnData(data.X, obs=data.obs, var=data.var))
        self._pert_data.load(data_path=f"{self._data_dir}/cellforge_train")
        self._pert_data.prepare_split(split="simulation", seed=seed)
        self._pert_data.get_dataloader(batch_size=int(config.get("batch_size", 32)), test_batch_size=int(config.get("test_batch_size", 128)))
        self._model = self._GEARS(self._pert_data, device=str(config.get("device", "cpu")))
        self._model.model_initialize(hidden_size=int(config.get("hidden_size", 64)))
        self._model.train(epochs=int(config.get("epochs", 20)))

    def predict(self, perturbations: Sequence[str], genes: Sequence[str]) -> np.ndarray:
        raw = self._model.predict([[name] for name in perturbations])
        if isinstance(raw, dict):
            raw = raw.get("pred", raw.get("prediction", raw))
        matrix = np.asarray(raw, dtype=np.float64)
        if matrix.ndim != 2:
            raise ValueError("GEARS backend prediction must be a two-dimensional gene-expression matrix")
        if matrix.shape[1] != len(genes):
            raise ValueError("GEARS prediction gene order/width does not match the CellForge dataset")
        return matrix


class GEARSAdapter:
    """Adapt GEARS predictions to CellForge's leakage-safe predictor contract."""

    name = "gears"
    information_access = "GEARS trained on the CellForge training partition only."

    def __init__(
        self,
        *,
        data_dir: str = "artifacts/gears",
        config: dict[str, Any] | None = None,
        seed: int = 0,
        backend: GEARSBackend | None = None,
    ) -> None:
        self.config = dict(config or {})
        self.seed = seed
        self.data_dir = data_dir
        self._backend = backend
        self._fitted = False
        self._identity = ModelIdentity("GEARS", "unknown", "cell-gears", self.config, seed)

    @property
    def identity(self) -> ModelIdentity:
        return self._identity

    def fit(self, train: Any, columns: SplitColumns) -> None:
        if self._backend is None:
            self._backend = _PackageGEARSBackend(self.data_dir, self.config)
        self._backend.fit(train, columns, self.config, self.seed)
        self._genes = tuple(map(str, train.var_names))
        self._control_mean = np.asarray(
            train[train.obs[columns.control].to_numpy(dtype=bool)].X.mean(axis=0), dtype=np.float64
        ).ravel()
        self._dataset_fingerprint = dataset_fingerprint(train)
        self._identity = ModelIdentity("GEARS", str(getattr(self._backend, "version", "unknown")), "cell-gears", self.config, self.seed)
        self._fitted = True

    def predict(self, perturbations: Sequence[str]) -> Predictions:
        if not self._fitted:
            raise RuntimeError("Call fit() before predict()")
        expression = self._backend.predict(tuple(map(str, perturbations)), self._genes)
        return Predictions(tuple(map(str, perturbations)), self._genes, expression, self._control_mean, tuple(True for _ in perturbations))

    def provenance(self, split_sha256: str, evaluation_perturbations: Sequence[str]) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("Call fit() before provenance()")
        return {
            "model": asdict(self._identity),
            "model_config_sha256": self._identity.config_sha256,
            "dataset_fingerprint": self._dataset_fingerprint,
            "split_sha256": split_sha256,
            "evaluation_perturbations": list(map(str, evaluation_perturbations)),
        }
