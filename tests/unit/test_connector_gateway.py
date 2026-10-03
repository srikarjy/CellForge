import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from cellforge.connectors import (
    ConnectorGateway,
    ConnectorPolicy,
    ConnectorSpec,
    StepRequest,
    ToolEffect,
    WorkflowRequest,
)
from cellforge.connectors.gateway import CallableConnector, WorkflowError


def _connector(name: str, provider: str = "mcp", effect: ToolEffect = ToolEffect.READ):
    async def invoke(arguments: Mapping[str, Any]) -> Any:
        await asyncio.sleep(0)
        return {"connector": name, "arguments": dict(arguments)}

    return CallableConnector(ConnectorSpec(name, "test.lookup", provider, effect), invoke)


def test_one_request_runs_several_connectors_in_dependency_order() -> None:
    gateway = ConnectorGateway(ConnectorPolicy(max_concurrency=2))
    gateway.register(_connector("geo_search", "claude"))
    gateway.register(_connector("cellxgene_lookup", "openai"))
    gateway.register(_connector("provenance_check", "local"))

    result = asyncio.run(
        gateway.run(
            WorkflowRequest(
                run_id="run-1",
                steps=(
                    StepRequest("geo", "geo_search", {"query": "GSE90063"}),
                    StepRequest("cellxgene", "cellxgene_lookup", {"query": "GSE90063"}),
                    StepRequest("verify", "provenance_check", depends_on=("geo", "cellxgene")),
                ),
            )
        )
    )

    assert result.status == "succeeded"
    assert [step.id for step in result.steps] == ["geo", "cellxgene", "verify"]
    assert len(result.manifest_sha256) == 64


def test_write_connector_requires_explicit_approval() -> None:
    gateway = ConnectorGateway()
    gateway.register(_connector("publish_report", effect=ToolEffect.WRITE))

    with pytest.raises(WorkflowError, match="write approval"):
        asyncio.run(
            gateway.run(
                WorkflowRequest("run-1", (StepRequest("publish", "publish_report"),))
            )
        )


def test_allowlist_and_step_limit_are_enforced() -> None:
    gateway = ConnectorGateway(
        ConnectorPolicy(max_steps=1, allowed_providers=frozenset({"openai"}))
    )
    gateway.register(_connector("geo_search", "claude"))

    with pytest.raises(WorkflowError, match="Provider is not allowed"):
        asyncio.run(
            gateway.run(WorkflowRequest("run-1", (StepRequest("geo", "geo_search"),)))
        )


def test_cycle_is_rejected() -> None:
    gateway = ConnectorGateway()
    gateway.register(_connector("lookup"))

    with pytest.raises(WorkflowError, match="cycle"):
        asyncio.run(
            gateway.run(
                WorkflowRequest(
                    "run-1",
                    (
                        StepRequest("a", "lookup", depends_on=("b",)),
                        StepRequest("b", "lookup", depends_on=("a",)),
                    ),
                )
            )
        )
