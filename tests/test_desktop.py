import json
import os
import runpy
import socket
import time
from pathlib import Path

import httpx
import pytest

from zyntrava.desktop import DesktopBackend, DesktopError
from zyntrava.sdk_example import demo


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_desktop_owns_authenticated_api_and_stops_without_persisting_credentials(tmp_path):
    backend = DesktopBackend(tmp_path / "state", free_port())
    backend.start()
    assert backend.runtime is not None
    token = backend.runtime.operator_token
    try:
        with httpx.Client(base_url=backend.url.removesuffix("/app/"), trust_env=False) as client:
            assert client.get("/app/").status_code == 200
            assert client.get("/overview").status_code == 401
            assert (
                client.get("/overview", headers={"Authorization": "Bearer " + token}).status_code
                == 200
            )
            assert client.get("/health", headers={"Host": "localhost"}).status_code == 403
            assert (
                client.get("/overview", headers={"Origin": "https://example.invalid"}).status_code
                == 403
            )
        for path in backend.state.rglob("*"):
            if path.is_file():
                assert token.encode() not in path.read_bytes()
    finally:
        backend.stop()
    assert backend.thread is not None and not backend.thread.is_alive()
    assert backend.runtime.operator_token == ""
    with pytest.raises(httpx.HTTPError), httpx.Client(trust_env=False, timeout=0.5) as client:
        client.get(backend.url)


def test_occupied_port_does_not_create_state_or_attach_to_other_service(tmp_path):
    with socket.socket() as existing:
        existing.bind(("127.0.0.1", 0))
        existing.listen()
        backend = DesktopBackend(tmp_path / "new", existing.getsockname()[1])
        with pytest.raises(DesktopError, match="Port is unavailable"):
            backend.start()
        assert not backend.state.exists()


def test_existing_uninitialized_state_is_never_overwritten(tmp_path):
    (tmp_path / "keep.txt").write_text("unrelated fixture")
    backend = DesktopBackend(tmp_path, free_port())
    with pytest.raises(DesktopError, match="nothing overwritten"):
        backend.start()
    assert (tmp_path / "keep.txt").read_text() == "unrelated fixture"
    assert not (tmp_path / "policy.json").exists()


def test_cancelled_launcher_cannot_start_later(tmp_path):
    backend = DesktopBackend(tmp_path / "state", free_port())
    backend.stop()
    with pytest.raises(DesktopError, match="already started or stopped"):
        backend.start()
    assert not backend.state.exists()


def test_startup_timeout_closes_socket_and_clears_in_memory_credentials(tmp_path):
    backend = DesktopBackend(tmp_path / "state", free_port())
    with pytest.raises(DesktopError, match="timed out"):
        backend.start(timeout=0)
    assert backend.runtime is not None and backend.runtime.operator_token == ""
    assert backend.thread is not None and not backend.thread.is_alive()


def test_corrupt_audit_fails_closed_with_safe_error(tmp_path):
    from zyntrava.startup import initialize_lab

    initialize_lab(tmp_path / "state")
    (tmp_path / "state/audit.sqlite3").write_bytes(b"not a database")
    backend = DesktopBackend(tmp_path / "state", free_port())
    with pytest.raises(DesktopError, match="Backend startup failed"):
        backend.start()
    assert backend.thread is None


def test_restart_rotates_credentials_and_preserves_workspace(tmp_path):
    state = tmp_path / "state"
    first = DesktopBackend(state, free_port())
    first.start()
    assert first.runtime is not None
    old = first.runtime.operator_token
    first.stop()
    (state / "workspace/public/keep.txt").write_text("operator fixture")
    second = DesktopBackend(state, free_port())
    try:
        second.start()
        with httpx.Client(trust_env=False) as client:
            assert (
                client.get(
                    second.url.removesuffix("/app/") + "/overview",
                    headers={"Authorization": "Bearer " + old},
                ).status_code
                == 401
            )
        assert (state / "workspace/public/keep.txt").read_text() == "operator fixture"
    finally:
        second.stop()


def test_sdk_example_runs_real_dispatch_with_scripted_decisions():
    result = json.loads(demo())
    assert result["neural_inference"] is False
    assert [d["status"] for d in result["decisions"]] == ["allowed", "blocked", "allowed"]


def test_installer_rejects_tampered_bundle_and_unowned_uninstall(tmp_path):
    installer = runpy.run_path(str(Path(__file__).resolve().parents[1] / "packaging/install.py"))
    (tmp_path / "requirements.txt").write_text("tampered")
    (tmp_path / "SHA256SUMS.json").write_text(
        json.dumps({"identity": installer["IDENTITY"], "files": {"requirements.txt": "0" * 64}})
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        installer["verified_bundle"](tmp_path)
    (tmp_path / "installation.json").write_text('{"identity":"someone-else"}')
    with pytest.raises(ValueError, match="ownership marker"):
        installer["uninstall"](tmp_path)
    assert (tmp_path / "requirements.txt").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows Tk desktop prototype")
def test_real_tk_window_copies_in_memory_credential_and_closes_backend(tmp_path, monkeypatch):
    import tkinter as tk
    from tkinter import ttk

    from zyntrava.desktop import launch

    original = tk.Tk
    opened = []
    outcomes = []
    errors = []
    port = free_port()

    def make_window():
        window = original()
        window.withdraw()
        deadline = time.monotonic() + 12

        def exercise():
            if not opened:
                if time.monotonic() > deadline:
                    errors.append("launcher did not open dashboard")
                    window.destroy()
                else:
                    window.after(50, exercise)
                return

            def buttons(widget):
                found = []
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        found.append(child)
                    found.extend(buttons(child))
                return found

            try:
                controls = {b.cget("text"): b for b in buttons(window)}
                window.deiconify()
                window.update_idletasks()
                assert all(
                    b.winfo_y() + b.winfo_height() <= b.master.winfo_height()
                    for b in controls.values()
                )
                controls["Copy operator credential"].invoke()
                token = window.clipboard_get()
                with httpx.Client(trust_env=False) as client:
                    response = client.get(
                        f"http://127.0.0.1:{port}/overview",
                        headers={"Authorization": "Bearer " + token},
                    )
                outcomes.append(
                    response.status_code == 200 and response.json()["connected_agents"] == 0
                )
                controls["Stop and close"].invoke()
            except Exception as exc:
                errors.append(type(exc).__name__)
                window.destroy()

        window.after(50, exercise)
        return window

    monkeypatch.setattr(tk, "Tk", make_window)
    monkeypatch.setattr("zyntrava.desktop.webbrowser.open", lambda url: opened.append(url) or True)
    launch(tmp_path / "state", port)
    assert not errors and outcomes == [True]
    assert opened == [f"http://127.0.0.1:{port}/app/"]
