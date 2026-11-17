"""Owned, credential-isolated local llama.cpp process. Never enables native tools."""

import hashlib
import json
import os
import secrets
import subprocess  # nosec B404 -- owned pinned local runtime, never model commands.
import time
from pathlib import Path
from typing import Any

import httpx


class LocalRuntime:
    def __init__(self, root: Path, port: int = 8790, *, model_name: str = "qwen2.5") -> None:
        if not 1024 <= port <= 65535:
            raise ValueError("invalid local model port")
        self.root = root
        manifests = {
            "qwen2.5": "local-model.json",
            "qwen3": "qwen3-0.6b.json",
            "qwen3-4b": "qwen3-4b.json",
        }
        if model_name not in manifests:
            raise ValueError("unsupported local model selection")
        self.config: dict[str, Any] = json.loads(
            (root / "models" / manifests[model_name]).read_text()
        )
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}/v1"
        self.token = secrets.token_urlsafe(32)
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        base = self.root / ".tools/local-model"
        weights = base / self.config["filename"]
        executable = base / "runtime/llama-server.exe"
        with weights.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != self.config["sha256"]:
                raise ValueError("model weight checksum mismatch")
        # Do not inherit provider credentials, proxy configuration or LLAMA_ARG_* settings.
        environment = {
            k: os.environ[k]
            for k in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
            if k in os.environ
        }
        environment["LLAMA_API_KEY"] = self.token
        command = [
            str(executable),
            "--model",
            str(weights),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--alias",
            self.config["model_id"],
            "--ctx-size",
            str(self.config["context_tokens"]),
            "--parallel",
            "1",
            "--gpu-layers",
            str(self.config["gpu_layers"]),
            "--jinja",
            "--no-webui",
            "--no-agent",
            "--no-webui-mcp-proxy",
            "--no-slots",
            "--no-cors-credentials",
            "--cors-origins",
            f"http://127.0.0.1:{self.port}",
            "--log-disable",
            "--threads",
            "4",
        ]
        if self.config.get("disable_thinking", False):
            command.extend(["--chat-template-kwargs", '{"enable_thinking":false}'])
        self.process = subprocess.Popen(  # noqa: S603 # nosec B603 -- fixed argv, no shell.
            command,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=int(vars(subprocess).get("CREATE_NO_WINDOW", 0))
            if os.name == "nt"
            else 0,
        )
        deadline = time.monotonic() + 60
        with httpx.Client(trust_env=False, timeout=1) as client:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError("local inference runtime exited during startup")
                try:
                    response = client.get(
                        f"http://127.0.0.1:{self.port}/health",
                        headers={"Authorization": f"Bearer {self.token}"},
                    )
                    if response.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
        self.stop()
        raise TimeoutError("local model did not become ready in 60 seconds")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    async def model(self, client: Any) -> Any:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            self.config["model_id"],
            provider=OpenAIProvider(base_url=self.base_url, api_key=self.token, http_client=client),
        )
