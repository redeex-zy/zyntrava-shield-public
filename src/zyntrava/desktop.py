"""Windows Tk launcher for the existing authenticated loopback API. No OS sandbox."""

import os
import socket
import threading
import time
import webbrowser
from pathlib import Path

import httpx
import uvicorn

from zyntrava.startup import LocalApplication, dashboard_path, initialize_lab, local_application


class DesktopError(RuntimeError):
    """Fixed, credential-free startup/status explanation safe to display."""


def default_state() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise DesktopError("LOCALAPPDATA is unavailable. Supply an explicit --state directory.")
    return Path(base) / "ZyntravaShield" / "Prototype" / "state"


class DesktopBackend:
    """Own the API thread and socket; credentials stay in memory, never in URLs or files."""

    def __init__(self, state: Path, port: int = 8765, *, root: Path | None = None) -> None:
        if not 1024 <= port <= 65535:
            raise DesktopError("Choose a port between 1024 and 65535.")
        self.state = state.resolve()
        # Installed launchers must not discover models/results from the caller's cwd.
        checkout = Path(__file__).resolve().parents[2]
        source_root = checkout if (checkout / "pyproject.toml").is_file() else self.state
        self.root = root if root is not None else source_root
        self.port = port
        self.runtime: LocalApplication | None = None
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None
        self.socket: socket.socket | None = None
        self.cancelled = threading.Event()
        self.lock = threading.RLock()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/app/"

    def start(self, timeout: float = 15) -> None:
        try:
            with self.lock:
                if self.cancelled.is_set() or self.thread is not None:
                    raise DesktopError("This launcher session has already started or stopped.")
                if not (dashboard_path(self.root) / "index.html").is_file():
                    raise DesktopError(
                        "Dashboard assets are missing. Install a desktop wheel "
                        "or build the dashboard."
                    )
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket = listener
                if os.name == "nt":
                    # Windows-only constant; keep exclusive bind mandatory on Windows.
                    exclusive = vars(socket)["SO_EXCLUSIVEADDRUSE"]
                    listener.setsockopt(socket.SOL_SOCKET, exclusive, 1)
                try:
                    listener.bind(("127.0.0.1", self.port))
                    listener.listen(128)
                except OSError:
                    raise DesktopError(
                        "Port is unavailable. Close the other service or use --port."
                    ) from None
                if not self.state.exists():
                    initialize_lab(self.state)
                if not (self.state / "policy.json").is_file():
                    raise DesktopError(
                        "Existing state is not initialized. Choose a new --state path; "
                        "nothing overwritten."
                    )
                self.runtime = local_application(self.state, self.root, self.port)
                self.server = uvicorn.Server(
                    uvicorn.Config(
                        self.runtime.app,
                        host="127.0.0.1",
                        port=self.port,
                        access_log=False,
                        log_level="error",
                        limit_concurrency=32,
                        timeout_keep_alive=5,
                        timeout_graceful_shutdown=3,
                    )
                )
                self.thread = threading.Thread(
                    target=self.server.run,
                    kwargs={"sockets": [listener]},
                    name="zyntrava-local-api",
                    daemon=True,
                )
                self.thread.start()
            deadline = time.monotonic() + timeout
            with httpx.Client(trust_env=False, timeout=0.5, follow_redirects=False) as client:
                while time.monotonic() < deadline and not self.cancelled.is_set():
                    if not self.thread.is_alive():
                        raise DesktopError(
                            "The backend exited during startup. Run serve in a terminal "
                            "to diagnose."
                        )
                    try:
                        result = client.get(
                            f"http://127.0.0.1:{self.port}/overview",
                            headers={"Authorization": "Bearer " + self.runtime.operator_token},
                        )
                        if result.status_code == 200 and self.server.started:
                            return
                    except httpx.HTTPError:
                        pass
                    self.cancelled.wait(0.05)
            raise DesktopError(
                "Backend startup timed out or was cancelled. No dashboard was opened."
            )
        except DesktopError:
            self.stop()
            raise
        except (OSError, ValueError):
            self.stop()
            raise DesktopError(
                "State could not be loaded. Check permissions/policy; existing files were retained."
            ) from None
        except Exception:
            self.stop()
            raise DesktopError(
                "Backend startup failed. Inspect state offline; no dashboard was opened."
            ) from None

    def stop(self) -> None:
        self.cancelled.set()
        with self.lock:
            if self.server is not None:
                self.server.should_exit = True
            if self.thread is not None and self.thread is not threading.current_thread():
                self.thread.join(timeout=8)
                if self.thread.is_alive():
                    raise DesktopError(
                        "Backend is still stopping. Wait for active requests to finish."
                    )
            if self.runtime is not None:
                self.runtime.control.close()
                self.runtime.operator_token = ""  # nosec B105 -- erase ephemeral credential.
                self.runtime.agent_token = ""  # nosec B105 -- erase ephemeral credential.
            if self.socket is not None:
                self.socket.close()


def launch(state: Path | None = None, port: int = 8765) -> None:
    if os.name != "nt":
        raise DesktopError(
            "The desktop prototype is supported on Windows only. Use serve elsewhere."
        )
    backend = DesktopBackend(state if state is not None else default_state(), port)
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        raise DesktopError(
            "Tk is unavailable. Use Python 3.13 with Tcl/Tk, or the terminal workflow."
        ) from None
    try:
        window = tk.Tk()
    except tk.TclError as exc:
        raise DesktopError(
            "Tk is unavailable. Install Python 3.13 with Tcl/Tk, "
            "or use the terminal serve workflow."
        ) from exc
    window.title("Zyntrava Shield - desktop prototype")
    window.geometry("680x520")
    window.minsize(640, 500)
    body = ttk.Frame(window, padding=24)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="ZYNTRAVA SHIELD", font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(body, text="Intelligence Deserves Protection.").pack(anchor="w", pady=(0, 14))
    ttk.Label(
        body,
        text="Experimental local launcher. Registered broker tools only.\n"
        "No system-wide protection or production OS isolation.\n"
        "Synthetic workspace; starting the backend does not connect an AI agent.",
        wraplength=580,
    ).pack(anchor="w")
    status = tk.StringVar(value="Starting authenticated localhost backend...")
    ttk.Label(body, textvariable=status, wraplength=580).pack(anchor="w", pady=14)
    ttk.Label(body, text=backend.url).pack(anchor="w")
    ttk.Label(
        body,
        text="Copy the operator credential, then paste it into the dashboard.\n"
        "Copying exposes it to the Windows clipboard until cleared or replaced.",
        wraplength=580,
    ).pack(anchor="w", pady=10)
    row = ttk.Frame(body)
    row.pack(anchor="w")
    copied = False
    finished = threading.Event()
    failed: list[str] = []

    def open_dashboard() -> None:
        try:
            opened = webbrowser.open(backend.url)
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            status.set("Browser could not open. Copy the displayed address into your browser.")

    def copy_credential() -> None:
        nonlocal copied
        if backend.runtime is not None:
            try:
                window.clipboard_clear()
                window.clipboard_append(backend.runtime.operator_token)
                copied = True
                status.set(
                    "Operator credential copied. Paste it in the dashboard; keep it private."
                )
            except tk.TclError:
                status.set("Clipboard unavailable. Use the terminal serve workflow instead.")

    opener = ttk.Button(row, text="Open dashboard", command=open_dashboard, state="disabled")
    opener.pack(side="left", padx=(0, 8))
    copier = ttk.Button(
        row, text="Copy operator credential", command=copy_credential, state="disabled"
    )
    copier.pack(side="left")

    def start() -> None:
        try:
            backend.start()
        except DesktopError as exc:
            failed.append(str(exc))
        finally:
            finished.set()

    def ready() -> None:
        if not finished.is_set():
            window.after(100, ready)
            return
        if failed:
            status.set(failed[0])
            return
        status.set("Backend ready on localhost. Protection covers registered broker calls only.")
        opener.configure(state="normal")
        copier.configure(state="normal")
        open_dashboard()

    def close() -> None:
        opener.configure(state="disabled")
        copier.configure(state="disabled")
        status.set("Stopping backend...")
        # Clipboard cleanup is best effort; do not erase unrelated clipboard contents.
        if copied and backend.runtime is not None:
            try:
                if window.clipboard_get() == backend.runtime.operator_token:
                    window.clipboard_clear()
            except tk.TclError:
                pass
        stopped = threading.Event()
        errors: list[str] = []

        def stop() -> None:
            try:
                backend.stop()
            except DesktopError as exc:
                errors.append(str(exc))
            finally:
                stopped.set()

        def check() -> None:
            if not stopped.is_set():
                window.after(100, check)
            elif errors:
                status.set(errors[0])
            else:
                window.destroy()

        threading.Thread(target=stop, daemon=True).start()
        check()

    window.protocol("WM_DELETE_WINDOW", close)
    ttk.Button(body, text="Stop and close", command=close).pack(anchor="w", pady=14)
    threading.Thread(target=start, daemon=True).start()
    window.after(100, ready)
    try:
        window.mainloop()
    finally:
        backend.stop()
