import numpy as np
import pandas as pd
from anndata import AnnData

from cellforge.models import GEARSAdapter
from cellforge.splits import SplitColumns


class FakeGEARS:
    version = "0.1.1-fixture"

    def fit(self, train, columns, config, seed):
        self.train_shape = train.shape
        self.seed = seed

    def predict(self, perturbations, genes):
        return np.tile(np.arange(1, len(genes) + 1, dtype=float), (len(perturbations), 1))


def test_gears_adapter_satisfies_cellforge_prediction_contract_and_provenance():
    obs = pd.DataFrame(
        {
            "target_genes": ["ctrl", "ctrl", "A", "A"],
            "is_control": [True, True, False, False],
            "assignment_class": ["non_targeting_control", "non_targeting_control", "single_target", "single_target"],
            "context": ["K562"] * 4,
        }
    )
    adata = AnnData(np.ones((4, 3)), obs=obs, var=pd.DataFrame(index=["G1", "G2", "G3"]))
    adapter = GEARSAdapter(backend=FakeGEARS(), config={"epochs": 1}, seed=7)
    columns = SplitColumns()
    adapter.fit(adata, columns)
    predictions = adapter.predict(["A"])
    predictions.validate()
    assert predictions.perturbations == ("A",)
    assert adapter.identity.name == "GEARS"
    provenance = adapter.provenance("split-hash", ["A"])
    assert provenance["model"]["version"] == "0.1.1-fixture"
    assert provenance["split_sha256"] == "split-hash"
