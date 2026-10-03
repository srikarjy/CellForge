"""A disposable, offline virtual desktop that an agent controls through a narrow API.

The agent never gets a shell. It sees screenshots and requests a small set of
validated actions; the host executes them with ``docker exec`` using argument
lists (never shell strings). The container has no network, a read-only root, no
capabilities, and resource limits.
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
APP_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "terminal": ("xterm", "-geometry", "110x32+20+20"),
}
KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_+]{0,39}$")
MAX_TYPE_CHARS = 500
MAX_SCROLL_CLICKS = 20


class DesktopError(RuntimeError):
    """The desktop backend failed (container, display, or command error)."""


class ActionRejected(ValueError):
    """An action violated the validation rules and was not executed."""


@dataclass(frozen=True)
class DesktopConfig:
    image: str = "cellforge-desktop:0.1"
    width: int = 1280
    height: int = 800
    memory: str = "1g"
    cpus: str = "1.0"
    pids_limit: int = 256
    command_timeout: float = 20.0
    max_screenshot_bytes: int = 5_000_000
    # (host_path, container_path) pairs mounted read-only, e.g. staged datasets.
    readonly_mounts: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ExecResult:
    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""


class Backend(Protocol):
    def start(self) -> None: ...

    def exec(self, argv: Sequence[str], *, detach: bool = False) -> ExecResult: ...

    def stop(self) -> None: ...


def build_run_command(config: DesktopConfig, name: str) -> list[str]:
    """The exact ``docker run`` invocation; isolation flags are fixed, not configurable."""

    command = [
        "docker", "run", "--detach", "--rm", "--init",
        "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=64m,mode=1777",
        "--tmpfs", "/home/agent:rw,size=64m,uid=1000,gid=1000",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", str(config.pids_limit),
        "--memory", config.memory,
        "--memory-swap", config.memory,
        "--cpus", config.cpus,
        "--user", "1000:1000",
        "--env", f"WIDTH={config.width}",
        "--env", f"HEIGHT={config.height}",
    ]
    for host_path, container_path in config.readonly_mounts:
        if not host_path.startswith("/") or not container_path.startswith("/"):
            raise ValueError("Mount paths must be absolute")
        if "," in host_path or "," in container_path:
            raise ValueError("Mount paths must not contain commas")
        command += [
            "--mount", f"type=bind,source={host_path},target={container_path},readonly"
        ]
    command.append(config.image)
    return command


class DockerBackend:
    """Runs one desktop container and executes commands inside it."""

    def __init__(self, config: DesktopConfig) -> None:
        self.config = config
        self.name = f"cellforge-desktop-{uuid.uuid4().hex[:12]}"

    def _docker(self, argv: Sequence[str]) -> ExecResult:
        try:
            done = subprocess.run(
                list(argv), capture_output=True, timeout=self.config.command_timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise DesktopError(f"Command timed out: {argv[:3]}") from exc
        return ExecResult(done.returncode, done.stdout, done.stderr)

    def start(self) -> None:
        result = self._docker(build_run_command(self.config, self.name))
        if result.returncode != 0:
            raise DesktopError(result.stderr.decode(errors="replace").strip())
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.exec(["xdpyinfo"]).returncode == 0:
                return
            time.sleep(0.25)
        self.stop()
        raise DesktopError("Virtual display did not start within 15s")

    def exec(self, argv: Sequence[str], *, detach: bool = False) -> ExecResult:
        command = ["docker", "exec", *(["--detach"] if detach else [])]
        command += ["--env", "DISPLAY=:99", self.name, *argv]
        return self._docker(command)

    def stop(self) -> None:
        subprocess.run(["docker", "rm", "--force", self.name], capture_output=True, timeout=30)


class VirtualDesktop:
    """Validated actions and observations over a backend."""

    def __init__(self, config: DesktopConfig | None = None, backend: Backend | None = None) -> None:
        self.config = config or DesktopConfig()
        self._backend = backend or DockerBackend(self.config)

    def __enter__(self) -> VirtualDesktop:
        self._backend.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._backend.stop()

    def screenshot(self) -> bytes:
        result = self._backend.exec(["import", "-window", "root", "png:-"])
        if result.returncode != 0:
            raise DesktopError(result.stderr.decode(errors="replace").strip())
        if not result.stdout.startswith(PNG_MAGIC):
            raise DesktopError("Screenshot is not a PNG image")
        if len(result.stdout) > self.config.max_screenshot_bytes:
            raise DesktopError("Screenshot exceeds the size limit")
        return result.stdout

    def click(self, x: int, y: int, button: int = 1, *, double: bool = False) -> None:
        self._check_point(x, y)
        if button not in (1, 2, 3):
            raise ActionRejected(f"Unsupported mouse button: {button}")
        click = ["click", "--repeat", "2", "--delay", "80", str(button)] if double else [
            "click", str(button)
        ]
        self._run(["xdotool", "mousemove", str(x), str(y), *click])

    def type_text(self, text: str) -> None:
        if not text or len(text) > MAX_TYPE_CHARS:
            raise ActionRejected(f"Text must be 1-{MAX_TYPE_CHARS} characters")
        if "\x00" in text:
            raise ActionRejected("Text must not contain NUL")
        # "--" stops xdotool from reading text that starts with "-" as an option.
        self._run(["xdotool", "type", "--delay", "20", "--", text])

    def key(self, name: str) -> None:
        if not KEY_PATTERN.fullmatch(name):
            raise ActionRejected(f"Invalid key name: {name!r}")
        self._run(["xdotool", "key", "--", name])

    def scroll(self, x: int, y: int, clicks: int) -> None:
        self._check_point(x, y)
        if clicks == 0 or abs(clicks) > MAX_SCROLL_CLICKS:
            raise ActionRejected(f"Scroll must be 1-{MAX_SCROLL_CLICKS} clicks")
        button = "5" if clicks > 0 else "4"
        self._run(
            ["xdotool", "mousemove", str(x), str(y), "click", "--repeat", str(abs(clicks)), button]
        )

    def open_app(self, name: str) -> None:
        argv = APP_ALLOWLIST.get(name)
        if argv is None:
            raise ActionRejected(f"App is not allowlisted: {name!r}")
        result = self._backend.exec(argv, detach=True)
        if result.returncode != 0:
            raise DesktopError(result.stderr.decode(errors="replace").strip())

    def _check_point(self, x: int, y: int) -> None:
        if not (0 <= x < self.config.width and 0 <= y < self.config.height):
            raise ActionRejected(f"Point ({x}, {y}) is outside the screen")

    def _run(self, argv: Sequence[str]) -> None:
        result = self._backend.exec(argv)
        if result.returncode != 0:
            raise DesktopError(result.stderr.decode(errors="replace").strip())
