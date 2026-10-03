from collections.abc import Sequence
from pathlib import Path

import pytest

from cellforge.world import (
    ActionRejected,
    ApprovalPolicy,
    Budget,
    Click,
    DesktopConfig,
    Done,
    Key,
    OpenApp,
    ScriptedPolicy,
    TraceRecorder,
    TypeText,
    VirtualDesktop,
    build_run_command,
    run_episode,
)
from cellforge.world.desktop import PNG_MAGIC, DesktopError, ExecResult

PNG = PNG_MAGIC + b"fake-image-bytes"


class FakeBackend:
    def __init__(self, screenshot: bytes = PNG) -> None:
        self.calls: list[tuple[list[str], bool]] = []
        self._screenshot = screenshot

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def exec(self, argv: Sequence[str], *, detach: bool = False) -> ExecResult:
        self.calls.append((list(argv), detach))
        if argv[0] == "import":
            return ExecResult(0, self._screenshot)
        return ExecResult(0)


def _desktop(backend: FakeBackend | None = None) -> tuple[VirtualDesktop, FakeBackend]:
    backend = backend or FakeBackend()
    return VirtualDesktop(DesktopConfig(), backend), backend


def test_run_command_fixes_isolation_flags() -> None:
    command = build_run_command(DesktopConfig(), "world-1")
    joined = " ".join(command)

    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--cap-drop ALL" in joined
    assert "no-new-privileges" in joined
    assert "--user 1000:1000" in joined
    assert command[-1] == "cellforge-desktop:0.1"


def test_readonly_mounts_are_readonly_and_validated() -> None:
    config = DesktopConfig(readonly_mounts=(("/data/dixit", "/data"),))
    command = build_run_command(config, "w")
    assert "type=bind,source=/data/dixit,target=/data,readonly" in command

    with pytest.raises(ValueError):
        build_run_command(DesktopConfig(readonly_mounts=(("relative", "/data"),)), "w")
    with pytest.raises(ValueError):
        build_run_command(DesktopConfig(readonly_mounts=(("/a,b", "/data"),)), "w")


def test_actions_become_argument_lists_without_a_shell() -> None:
    desktop, backend = _desktop()
    desktop.click(10, 20)
    desktop.type_text("-rf; echo $(whoami)")
    desktop.key("ctrl+c")

    assert backend.calls[0][0] == ["xdotool", "mousemove", "10", "20", "click", "1"]
    # Text is one argv entry after "--", so shell syntax and leading dashes are inert.
    assert backend.calls[1][0] == [
        "xdotool", "type", "--delay", "20", "--", "-rf; echo $(whoami)"
    ]
    assert backend.calls[2][0] == ["xdotool", "key", "--", "ctrl+c"]


@pytest.mark.parametrize(
    "call",
    [
        lambda d: d.click(-1, 0),
        lambda d: d.click(1280, 0),
        lambda d: d.click(0, 800),
        lambda d: d.click(1, 1, button=9),
        lambda d: d.type_text(""),
        lambda d: d.type_text("x" * 501),
        lambda d: d.key("--help"),
        lambda d: d.key("a b"),
        lambda d: d.scroll(5, 5, 0),
        lambda d: d.scroll(5, 5, 99),
        lambda d: d.open_app("rm -rf /"),
        lambda d: d.open_app("bash"),
    ],
)
def test_invalid_actions_are_rejected_before_execution(call) -> None:
    desktop, backend = _desktop()
    with pytest.raises(ActionRejected):
        call(desktop)
    assert backend.calls == []


def test_open_app_uses_allowlist_and_detaches() -> None:
    desktop, backend = _desktop()
    desktop.open_app("terminal")
    argv, detach = backend.calls[0]
    assert argv[0] == "xterm" and detach is True


def test_non_png_screenshot_is_rejected() -> None:
    desktop, _ = _desktop(FakeBackend(screenshot=b"<html>not an image</html>"))
    with pytest.raises(DesktopError, match="PNG"):
        desktop.screenshot()


def test_episode_runs_script_and_records_trace(tmp_path: Path) -> None:
    desktop, _ = _desktop()
    recorder = TraceRecorder(tmp_path / "run")
    result = run_episode(
        desktop,
        ScriptedPolicy([OpenApp("terminal"), TypeText("ls"), Key("Return"), Done("ok")]),
        Budget(max_steps=10),
        recorder,
    )

    assert result.status == "done" and result.steps == 4
    assert len(list((tmp_path / "run").glob("step_*.png"))) == 4
    assert len((tmp_path / "run" / "trace.jsonl").read_text().splitlines()) == 4


def test_trace_hash_is_deterministic_and_order_sensitive(tmp_path: Path) -> None:
    def run(directory: str, actions: list) -> str:
        desktop, _ = _desktop()
        recorder = TraceRecorder(tmp_path / directory)
        return run_episode(desktop, ScriptedPolicy(actions), Budget(), recorder).trace_sha256

    a = run("a", [Key("Return"), TypeText("x")])
    b = run("b", [Key("Return"), TypeText("x")])
    c = run("c", [TypeText("x"), Key("Return")])

    assert a == b
    assert a != c


def test_step_budget_stops_runaway_policy(tmp_path: Path) -> None:
    class Forever:
        def decide(self, observation):
            return Key("a")

    desktop, _ = _desktop()
    result = run_episode(desktop, Forever(), Budget(max_steps=3), TraceRecorder(tmp_path))
    assert result.status == "budget_steps" and result.steps == 3


def test_rejected_action_ends_episode_without_executing(tmp_path: Path) -> None:
    desktop, backend = _desktop()
    result = run_episode(
        desktop, ScriptedPolicy([OpenApp("bash")]), Budget(), TraceRecorder(tmp_path)
    )
    assert result.status == "rejected"
    assert all(argv[0] != "bash" for argv, _ in backend.calls)


def test_unapproved_risky_action_is_not_executed(tmp_path: Path) -> None:
    desktop, backend = _desktop()
    approval = ApprovalPolicy(required=lambda a: isinstance(a, TypeText), approve=lambda a: False)
    result = run_episode(
        desktop,
        ScriptedPolicy([Click(5, 5), TypeText("submit")]),
        Budget(),
        TraceRecorder(tmp_path),
        approval,
    )

    assert result.status == "denied"
    assert not any(argv[:2] == ["xdotool", "type"] for argv, _ in backend.calls)
