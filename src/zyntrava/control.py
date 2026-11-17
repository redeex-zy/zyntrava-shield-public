"""Operator control plane; never registered as agent tools."""

import importlib.util
import json
import os
import re
import subprocess  # nosec B404 -- fixed trusted synthetic CLI, never model commands.
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import psutil
from pydantic import Field

from zyntrava import __version__
from zyntrava.broker import Broker
from zyntrava.models import StrictModel, ToolRequest
from zyntrava.policy import Policy


class Settings(StrictModel):
    retention_days: int = Field(default=7, ge=1, le=365)
    poll_seconds: int = Field(default=5, ge=2, le=60)
    protection_mode: Literal["full"] = "full"


class JobRequest(StrictModel):
    kind: Literal["trace", "live", "demo", "recovery-demo"]
    corpus_version: Literal[1, 2, 3] = 2
    model: Literal["qwen2.5", "qwen3"] = "qwen2.5"
    include_release: bool = False
    repeats: int = Field(default=1, ge=1, le=3)


class PolicyUpdate(StrictModel):
    expected_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: dict[str, Any]


class Control:
    def __init__(self, root: Path, state: Path, broker: Broker) -> None:
        self.root, self.state, self.broker = root, state, broker
        state.mkdir(parents=True, exist_ok=True)
        settings_path = state / "settings.json"
        self.settings = (
            Settings.model_validate_json(settings_path.read_text())
            if settings_path.is_file()
            else Settings()
        )
        self.jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="zyntrava-lab")
        self.model_connected = False
        self.trace_process: subprocess.Popen[str] | None = None

    def corpus(self, version: int) -> Path:
        candidate = self.root / f"benchmarks/corpus-v{version}.json"
        return (
            candidate
            if candidate.is_file()
            else Path(__file__).parent / f"data/corpus-v{version}.json"
        )

    def available_jobs(self) -> list[str]:
        desktop = (Path(__file__).parent / "data/build-profile.json").is_file()
        return ["demo", "recovery-demo"] if desktop else ["demo", "recovery-demo", "trace", "live"]

    def output_dirs(self) -> tuple[Path, ...]:
        return (
            self.root / "benchmarks/results",
            self.root / "benchmarks/live-results",
            self.root / "benchmarks/evaluation-v4",
            self.root / "benchmarks/phase4-live-results",
            self.state / "research-results",
        )

    def result_path(self, experiment_id: str) -> Path:
        if not re.fullmatch(r"(?:trace|live)-\d{8}T\d{6}Z-[0-9a-f]{8}", experiment_id):
            raise ValueError("invalid experiment identifier")
        for directory in self.output_dirs():
            path = directory / f"{experiment_id}.json"
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= 20_000_000:
                return path
        raise ValueError("experiment not found")

    def results(self) -> list[dict[str, Any]]:
        items = {}
        for directory in self.output_dirs():
            if not directory.exists():
                continue
            for path in directory.glob("*.json"):
                try:
                    valid_path = self.result_path(path.stem)
                    data = json.loads(valid_path.read_text(encoding="utf-8"))
                    items[path.stem] = {
                        "experiment_id": data["experiment_id"],
                        "created_at": data["created_at"],
                        "kind": data["kind"],
                        "corpus_version": data.get("corpus_version"),
                        "corpus_sha256": data.get("corpus_sha256"),
                        "model_id": data.get("model", {}).get("model_id"),
                        "suite": data.get("suite"),
                        "repeats": data.get("repeats"),
                        "seed": data.get("seed"),
                        "metrics": {
                            m: r["splits"]["heldout"] for m, r in data.get("results", {}).items()
                        },
                        "evaluation_methodologies": data.get(
                            "evaluation_methodologies", ["legacy-static"]
                        ),
                        "execution_metrics": {
                            m: r["execution_aware_splits"]["heldout"]
                            for m, r in data.get("results", {}).items()
                            if "execution_aware_splits" in r
                        },
                        "limitations": data.get("limitations", []),
                        "live_rows": len(data.get("rows", [])),
                    }
                except (ValueError, KeyError, OSError, TypeError, AttributeError):
                    continue
        return sorted(items.values(), key=lambda row: row["created_at"], reverse=True)

    def integrations(self) -> list[dict[str, Any]]:
        installed = (self.root / ".tools/local-model/runtime/llama-server.exe").is_file() and (
            self.root / ".tools/local-model/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        ).is_file()
        dependency = importlib.util.find_spec("pydantic_ai") is not None
        live_results = [r for r in self.results() if r["kind"] == "live-local-model-synthetic-lab"]
        return [
            {
                "id": "pydantic-ai-local",
                "name": "Pydantic AI · local Qwen",
                "connected": self.model_connected,
                "installed": installed and dependency,
                "status": "connected" if self.model_connected else "disconnected",
                "last_experiment": live_results[0]["experiment_id"] if live_results else None,
                "coverage": "Registered broker tools only; native tools disabled; no OS sandbox.",
                "permissions": [
                    "read_file",
                    "write_file (operator approval)",
                    "post_message",
                    "fetch_page (explicit scope)",
                    "export_count (opt-in exact release rule, lab only)",
                ],
            },
            {
                "id": "scripted-fixture",
                "name": "Scripted framework fixture",
                "connected": False,
                "installed": dependency,
                "status": "demo-only",
                "last_experiment": None,
                "coverage": "Deterministic FunctionModel test double; no neural inference.",
                "permissions": ["read_file", "write_file", "post_message"],
            },
        ]

    def overview(self) -> dict[str, Any]:
        return {
            **self.broker.overview(),
            "connected_agents": int(self.model_connected),
            "protection_state": "active" if self.broker.mode == "full" else "partial",
            "workspace_mode": "synthetic",
            "version": __version__,
            "available_jobs": self.available_jobs(),
        }

    def update_policy(self, request: PolicyUpdate) -> str:
        policy = Policy.model_validate_json(json.dumps(request.policy))
        with self.broker._lock:
            if self.broker.policy.digest != request.expected_digest:
                raise ValueError("stale policy")
            self.broker.audit.append(
                phase="configuration",
                status="policy_update_requested",
                execution="not_run",
                detected=False,
                simulated=self.broker.simulated,
                old_digest=self.broker.policy.digest,
                new_digest=policy.digest,
            )
            target = self.state / "policy.json"
            temporary = target.with_suffix(".json.pending")
            temporary.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(target)
            self.broker.policy = policy
            return policy.digest

    def update_settings(self, settings: Settings) -> None:
        with self.lock:
            temporary = self.state / "settings.json.pending"
            temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.state / "settings.json")
            self.settings = settings
            self.broker.audit.purge_before(
                (datetime.now(UTC) - timedelta(days=settings.retention_days)).isoformat()
            )

    def start_job(self, request: JobRequest) -> dict[str, Any]:
        with self.lock:
            if request.kind not in self.available_jobs():
                raise ValueError(
                    "Research datasets and models are excluded from this desktop bundle"
                )
            if any(j["status"] in {"queued", "running"} for j in self.jobs.values()):
                raise ValueError("a research job is already running")
            if len(self.jobs) >= 100:
                raise ValueError("job capacity reached; restart the local service")
            if request.kind == "live" and not self.integrations()[0]["installed"]:
                raise ValueError(
                    "install the pinned local model and optional agent dependency first"
                )
            if (
                request.kind == "live"
                and request.model == "qwen3"
                and not (self.root / ".tools/local-model/Qwen3-0.6B-Q8_0.gguf").is_file()
            ):
                raise ValueError("install the pinned qwen3 model first")
            job_id = str(uuid4())
            job = {
                "id": job_id,
                "kind": request.kind,
                "status": "queued",
                "experiment_id": None,
                "created_at": datetime.now(UTC).isoformat(),
                "error": None,
            }
            self.jobs[job_id] = job
            self.executor.submit(self._work, job_id, request)
            return dict(job)

    def _work(self, job_id: str, request: JobRequest) -> None:
        with self.lock:
            self.jobs[job_id]["status"] = "running"
        try:
            if request.kind == "demo":
                session = self.broker.create_session()
                for tool, arguments in [
                    ("read_file", {"path": "public/hello.txt"}),
                    ("read_file", {"path": "private/forbidden.txt"}),
                    (
                        "write_file",
                        {
                            "path": f"reports/demo-{job_id[:8]}.txt",
                            "content": "Synthetic public report; review before execution.",
                        },
                    ),
                ]:
                    self.broker.submit(
                        session, ToolRequest.model_validate({"tool": tool, "arguments": arguments})
                    )
                experiment = None
            elif request.kind == "recovery-demo":
                from zyntrava.lab.recovery_demo import run_demo

                run_demo(self.state, self.broker.audit)
                experiment = None
            elif request.kind == "trace":
                # tracemalloc is process-global. Running it inside the API process
                # also traces concurrent dashboard JSON parsing and stalls requests.
                environment = {
                    key: os.environ[key]
                    for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
                    if key in os.environ
                }
                command = [
                    sys.executable,
                    "-m",
                    "zyntrava",
                    "adversarial" if request.corpus_version == 3 else "benchmark",
                    "--corpus",
                    str(self.corpus(request.corpus_version).resolve()),
                    "--output",
                    str((self.state / "research-results").resolve()),
                    "--repeats",
                    str(request.repeats),
                ]
                child = subprocess.Popen(  # noqa: S603 # nosec B603
                    command,
                    cwd=self.root,
                    env=environment,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=int(vars(subprocess).get("CREATE_NO_WINDOW", 0)),
                )
                with self.lock:
                    self.trace_process = child
                try:
                    stdout, _ = child.communicate(timeout=240)
                    match = re.search(r"trace-\d{8}T\d{6}Z-[0-9a-f]{8}", stdout)
                    if child.returncode != 0 or match is None:
                        raise RuntimeError("isolated synthetic trace job failed")
                    experiment = match[0]
                finally:
                    self._stop_trace()
            else:
                from zyntrava.lab.live import run_live

                path = run_live(
                    self.root,
                    self.state / "research-results",
                    request.repeats,
                    on_connection=self._connection,
                    model_name=request.model,
                    include_release=request.include_release,
                )
                experiment = path.stem
                # Import actual redacted tool events, preserving their original observation time.
                for row in json.loads(path.read_text())["rows"]:
                    for event in row["events"]:
                        original_time = event.pop("created_at")
                        event.pop("id", None)
                        self.broker.audit.append(
                            **event, observed_at=original_time, experiment_id=experiment
                        )
            with self.lock:
                self.jobs[job_id].update(status="completed", experiment_id=experiment)
        except Exception as exc:
            with self.lock:
                self.jobs[job_id].update(status="failed", error=type(exc).__name__)

    def _connection(self, connected: bool) -> None:
        self.model_connected = connected

    def close(self) -> None:
        self._stop_trace()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _stop_trace(self) -> None:
        with self.lock:
            child = self.trace_process
            self.trace_process = None
        if child is None:
            return
        try:
            owned = [psutil.Process(child.pid), *psutil.Process(child.pid).children(recursive=True)]
            for member in reversed(owned):
                try:
                    member.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(owned, timeout=5)
            for member in alive:
                member.kill()
        except psutil.NoSuchProcess:
            pass
        child.wait(timeout=5)
