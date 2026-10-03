"""Runs against a real container. Skipped unless Docker and the desktop image exist.

Build the image first:  docker build -t cellforge-desktop:0.1 docker/desktop
"""

import shutil
import subprocess
import time

import pytest

from cellforge.world import (
    Budget,
    DesktopConfig,
    Done,
    OpenApp,
    ScriptedPolicy,
    TraceRecorder,
    VirtualDesktop,
    run_episode,
)
from cellforge.world.desktop import PNG_MAGIC

IMAGE = DesktopConfig().image


def _image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _image_available(), reason="desktop image not built")


def test_screenshot_and_terminal_change_the_display(tmp_path) -> None:
    with VirtualDesktop() as desktop:
        before = desktop.screenshot()
        result = run_episode(
            desktop,
            ScriptedPolicy([OpenApp("terminal"), Done("opened")]),
            Budget(max_steps=5),
            TraceRecorder(tmp_path),
        )
        # The window draws asynchronously after the app is launched; poll briefly.
        deadline = time.monotonic() + 5
        after = desktop.screenshot()
        while after == before and time.monotonic() < deadline:
            time.sleep(0.25)
            after = desktop.screenshot()

    assert before.startswith(PNG_MAGIC) and after.startswith(PNG_MAGIC)
    assert result.status == "done"
    assert before != after


def test_container_is_offline_and_read_only() -> None:
    with VirtualDesktop() as desktop:
        backend = desktop._backend
        network = backend.exec(["bash", "-c", "exec 3<>/dev/tcp/1.1.1.1/53"])
        write = backend.exec(["bash", "-c", "touch /usr/should_fail"])

    assert network.returncode != 0
    assert write.returncode != 0
