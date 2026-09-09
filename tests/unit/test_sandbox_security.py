from pathlib import Path


SANDBOX = Path(__file__).parents[2] / "sandbox" / "index.html"


def test_sandbox_has_restrictive_browser_policy() -> None:
    html = SANDBOX.read_text()
    assert "Content-Security-Policy" in html
    assert "connect-src 'none'" in html
    assert "object-src 'none'" in html


def test_sandbox_bounds_uploaded_file_size() -> None:
    html = SANDBOX.read_text()
    assert "MAX_FILE_BYTES = 25 * 1024 * 1024" in html
    assert "file.size > MAX_FILE_BYTES" in html


def test_sandbox_does_not_upload_artifacts() -> None:
    html = SANDBOX.read_text()
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "navigator.sendBeacon" not in html
