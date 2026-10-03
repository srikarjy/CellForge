"""Execute several approved connectors through one bounded workflow call.

The gateway is provider-neutral. ChatGPT, Claude, or MCP clients can register
their available tools as ``Connector`` implementations without giving the
gateway credentials or unrestricted access to an entire connector catalog.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Mapping, Protocol


class ToolEffect(str, Enum):
    """Externally visible effect of a connector call."""

    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ConnectorSpec:
    """Metadata used to discover and authorize a connector."""

    name: str
    capability: str
    provider: str
    effect: ToolEffect = ToolEffect.READ
    description: str = ""


class Connector(Protocol):
    """Adapter implemented by an MCP, ChatGPT, Claude, or local tool."""

    spec: ConnectorSpec

    async def invoke(self, arguments: Mapping[str, Any]) -> Any:
        """Invoke the connector with validated, provider-specific arguments."""


@dataclass(frozen=True)
class StepRequest:
    """One connector operation in a workflow."""

    id: str
    connector: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowRequest:
    """A single request containing several connector operations."""

    run_id: str
    steps: tuple[StepRequest, ...]
    approve_writes: bool = False
    approve_destructive: bool = False


@dataclass(frozen=True)
class ConnectorPolicy:
    """Resource and authorization limits for one workflow call."""

    max_steps: int = 12
    max_concurrency: int = 4
    timeout_seconds: float = 30.0
    allowed_providers: frozenset[str] = frozenset()
    allowed_connectors: frozenset[str] = frozenset()


@dataclass(frozen=True)
class StepResult:
    id: str
    connector: str
    provider: str
    status: str
    started_at_unix: float
    duration_ms: int
    output: Any = None
    error: str | None = None


@dataclass(frozen=True)
class WorkflowResult:
    run_id: str
    status: str
    steps: tuple[StepResult, ...]
    manifest_sha256: str


class WorkflowError(ValueError):
    """Raised when a workflow is malformed or violates policy."""


class CallableConnector:
    """Small adapter for registering an async Python callable."""

    def __init__(
        self,
        spec: ConnectorSpec,
        function: Callable[[Mapping[str, Any]], Awaitable[Any]],
    ) -> None:
        self.spec = spec
        self._function = function

    async def invoke(self, arguments: Mapping[str, Any]) -> Any:
        return await self._function(arguments)


class ConnectorGateway:
    """Registry and bounded DAG executor used by the single workflow call."""

    def __init__(self, policy: ConnectorPolicy | None = None) -> None:
        self.policy = policy or ConnectorPolicy()
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        name = connector.spec.name
        if not name or name in self._connectors:
            raise WorkflowError(f"Connector name is empty or already registered: {name!r}")
        self._connectors[name] = connector

    def discover(self, capability: str | None = None) -> tuple[ConnectorSpec, ...]:
        specs = (connector.spec for connector in self._connectors.values())
        return tuple(
            sorted(
                (spec for spec in specs if capability is None or spec.capability == capability),
                key=lambda spec: (spec.capability, spec.provider, spec.name),
            )
        )

    async def run(self, request: WorkflowRequest) -> WorkflowResult:
        """Execute all dependency-ready steps and return one normalized result."""

        self._validate(request)
        pending = {step.id: step for step in request.steps}
        completed: dict[str, StepResult] = {}
        semaphore = asyncio.Semaphore(self.policy.max_concurrency)

        async def execute(step: StepRequest) -> StepResult:
            connector = self._connectors[step.connector]
            started = time.time()
            try:
                async with semaphore:
                    output = await asyncio.wait_for(
                        connector.invoke(step.arguments), timeout=self.policy.timeout_seconds
                    )
                return StepResult(
                    step.id,
                    connector.spec.name,
                    connector.spec.provider,
                    "succeeded",
                    started,
                    round((time.time() - started) * 1000),
                    output=output,
                )
            except TimeoutError:
                error = f"Connector exceeded {self.policy.timeout_seconds:g}s timeout"
            except Exception as exc:  # Connector boundary: normalize provider failures.
                error = f"{type(exc).__name__}: {exc}"
            return StepResult(
                step.id,
                connector.spec.name,
                connector.spec.provider,
                "failed",
                started,
                round((time.time() - started) * 1000),
                error=error,
            )

        while pending:
            blocked = [
                step
                for step in pending.values()
                if any(completed[dep].status != "succeeded" for dep in step.depends_on if dep in completed)
            ]
            for step in blocked:
                completed[step.id] = StepResult(
                    step.id,
                    step.connector,
                    self._connectors[step.connector].spec.provider,
                    "skipped",
                    time.time(),
                    0,
                    error="A dependency failed or was skipped",
                )
                pending.pop(step.id)

            ready = [
                step for step in pending.values() if all(dep in completed for dep in step.depends_on)
            ]
            if not ready:
                raise WorkflowError("Workflow dependencies contain a cycle")
            results = await asyncio.gather(*(execute(step) for step in ready))
            for result in results:
                completed[result.id] = result
                pending.pop(result.id)

        ordered = tuple(completed[step.id] for step in request.steps)
        status = "succeeded" if all(step.status == "succeeded" for step in ordered) else "failed"
        manifest = {
            "run_id": request.run_id,
            "status": status,
            "steps": [asdict(step) for step in ordered],
        }
        digest = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        return WorkflowResult(request.run_id, status, ordered, digest)

    def _validate(self, request: WorkflowRequest) -> None:
        if not request.run_id.strip():
            raise WorkflowError("run_id is required")
        if not request.steps:
            raise WorkflowError("At least one workflow step is required")
        if len(request.steps) > self.policy.max_steps:
            raise WorkflowError(f"Workflow exceeds the {self.policy.max_steps}-step limit")

        ids = [step.id for step in request.steps]
        if any(not step_id.strip() for step_id in ids) or len(ids) != len(set(ids)):
            raise WorkflowError("Step IDs must be non-empty and unique")
        known_ids = set(ids)
        for step in request.steps:
            if step.connector not in self._connectors:
                raise WorkflowError(f"Unknown connector: {step.connector}")
            if step.id in step.depends_on or any(dep not in known_ids for dep in step.depends_on):
                raise WorkflowError(f"Step {step.id!r} has invalid dependencies")
            spec = self._connectors[step.connector].spec
            if self.policy.allowed_providers and spec.provider not in self.policy.allowed_providers:
                raise WorkflowError(f"Provider is not allowed: {spec.provider}")
            if self.policy.allowed_connectors and spec.name not in self.policy.allowed_connectors:
                raise WorkflowError(f"Connector is not allowed: {spec.name}")
            if spec.effect is ToolEffect.WRITE and not request.approve_writes:
                raise WorkflowError(f"Connector requires write approval: {spec.name}")
            if spec.effect is ToolEffect.DESTRUCTIVE and not request.approve_destructive:
                raise WorkflowError(f"Connector requires destructive approval: {spec.name}")
