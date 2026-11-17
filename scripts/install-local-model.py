"""Download pinned public research assets. No accounts, credentials or cloud inference."""

import argparse
import hashlib
import json
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cli = argparse.ArgumentParser()
cli.add_argument("--model", choices=["qwen2.5", "qwen3", "qwen3-4b"], default="qwen2.5")
selected = cli.parse_args().model
manifest = {"qwen2.5": "local-model.json", "qwen3": "qwen3-0.6b.json", "qwen3-4b": "qwen3-4b.json"}[
    selected
]
CONFIG = json.loads((ROOT / "models" / manifest).read_text())
TARGET = ROOT / ".tools/local-model"
TARGET.mkdir(parents=True, exist_ok=True)


def download(url: str, target: Path, expected: str) -> None:
    if target.exists():
        with target.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() == expected:
                print(f"Already verified: {target.name}", flush=True)
                return
    partial = target.with_suffix(target.suffix + ".partial")
    digest = hashlib.sha256()
    size = 0
    last = time.monotonic()
    # Fixed HTTPS URLs from the pinned configuration, not agent-controlled destinations.
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as handle:  # noqa: S310
        while block := response.read(1024 * 1024):
            handle.write(block)
            digest.update(block)
            size += len(block)
            if time.monotonic() - last > 10:
                print(f"{target.name}: {size // 1048576} MiB downloaded", flush=True)
                last = time.monotonic()
    if digest.hexdigest() != expected:
        raise ValueError(f"Checksum mismatch for {target.name}; refusing asset")
    partial.replace(target)
    print(f"Verified SHA-256: {target.name}", flush=True)


runtime = TARGET / "runtime.zip"
download(CONFIG["runtime_url"], runtime, CONFIG["runtime_sha256"])
with zipfile.ZipFile(runtime) as archive:
    if any(Path(n).is_absolute() or ".." in Path(n).parts for n in archive.namelist()):
        raise ValueError("Unsafe archive member")
    # Retain already verified installed bytes; do not replace loaded runtime DLLs.
    for member in archive.infolist():
        target = TARGET / "runtime" / member.filename
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            content = archive.read(member)
            if not target.exists() or target.read_bytes() != content:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
model_url = (
    f"https://huggingface.co/{CONFIG['repository']}/resolve/{CONFIG['revision']}/"
    f"{CONFIG['filename']}"
)
download(model_url, TARGET / CONFIG["filename"], CONFIG["sha256"])
print("Pinned local model and Vulkan runtime installed. Weights are not redistributed.")
