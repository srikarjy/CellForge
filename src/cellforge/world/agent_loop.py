"""Observe-decide-act loop with budgets and human approval hooks."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Protocol, Union

from cellforge.world.desktop import ActionRejected, DesktopError, VirtualDesktop
from cellforge.world.trace import TraceRecorder


@dataclass(frozen=True)
class Click:
    x: int
    y: int
    button: int = 1
    double: bool = False


@dataclass(frozen=True)
class TypeText:
    text: str


@dataclass(frozen=True)
class Key:
    name: str


@dataclass(frozen=True)
class Scroll:
    x: int
    y: int
    clicks: int


@dataclass(frozen=True)
class OpenApp:
    name: str


@dataclass(frozen=True)
class Wait:
    seconds: float = 1.0


@dataclass(frozen=True)
class Done:
    message: str = ""


Action = Union[Click, TypeText, Key, Scroll, OpenApp, Wait, Done]
MAX_WAIT_SECONDS = 5.0


@dataclass(frozen=True)
class Observation:
    step: int
    screenshot: bytes


class Policy(Protocol):
    def decide(self, observation: Observation) -> Action: ...


@dataclass(frozen=True)
class Budget:
    max_steps: int = 30
    max_seconds: float = 120.0


@dataclass(frozen=True)
class ApprovalPolicy:
    """``required`` flags risky actions; ``approve`` is the human (or reviewer) decision."""

    required: Callable[[Action], bool]
    approve: Callable[[Action], bool]


@dataclass(frozen=True)
class EpisodeResult:
    status: str  # done | budget_steps | budget_time | rejected | denied | error
    steps: int
    reason: str
    trace_sha256: str


class ScriptedPolicy:
    """Replays a fixed action list; used to test the loop without any model."""

    def __init__(self, actions: Iterable[Action]) -> None:
        self._actions = iter(actions)

    def decide(self, observation: Observation) -> Action:
        return next(self._actions, Done("script finished"))


def _apply(desktop: VirtualDesktop, action: Action) -> None:
    if isinstance(action, Click):
        desktop.click(action.x, action.y, action.button, double=action.double)
    elif isinstance(action, TypeText):
        desktop.type_text(action.text)
    elif isinstance(action, Key):
        desktop.key(action.name)
    elif isinstance(action, Scroll):
        desktop.scroll(action.x, action.y, action.clicks)
    elif isinstance(action, OpenApp):
        desktop.open_app(action.name)
    elif isinstance(action, Wait):
        time.sleep(min(max(action.seconds, 0.0), MAX_WAIT_SECONDS))
    else:  # pragma: no cover - guarded by the Action union
        raise ActionRejected(f"Unknown action: {action!r}")


def run_episode(
    desktop: VirtualDesktop,
    policy: Policy,
    budget: Budget,
    recorder: TraceRecorder,
    approval: ApprovalPolicy | None = None,
) -> EpisodeResult:
    """Run until the policy is done or a budget, rejection, or denial stops it."""

    started = time.monotonic()

    def finish(status: str, steps: int, reason: str) -> EpisodeResult:
        return EpisodeResult(status, steps, reason, recorder.trace_sha256)

    for step in range(1, budget.max_steps + 1):
        if time.monotonic() - started > budget.max_seconds:
            return finish("budget_time", step - 1, "Wall-clock budget exhausted")
        try:
            screenshot = desktop.screenshot()
        except DesktopError as exc:
            return finish("error", step - 1, str(exc))

        action = policy.decide(Observation(step, screenshot))
        payload = {"type": type(action).__name__, **asdict(action)}
        if isinstance(action, Done):
            recorder.record(step, payload, screenshot, "done")
            return finish("done", step, action.message)
        if approval and approval.required(action) and not approval.approve(action):
            recorder.record(step, payload, screenshot, "denied")
            return finish("denied", step, "Action was not approved")
        try:
            _apply(desktop, action)
        except ActionRejected as exc:
            recorder.record(step, payload, screenshot, f"rejected: {exc}")
            return finish("rejected", step, str(exc))
        except DesktopError as exc:
            recorder.record(step, payload, screenshot, f"error: {exc}")
            return finish("error", step, str(exc))
        recorder.record(step, payload, screenshot)

    return finish("budget_steps", budget.max_steps, "Step budget exhausted")
