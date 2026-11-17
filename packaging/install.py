"""Local Windows prototype installer: verified wheelhouse, no accounts, no elevated rights."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 -- fixed Python/pip argv, never agent-generated commands.
import sys
import venv
from pathlib import Path

IDENTITY = "zyntrava-desktop-prototype-v1"


class SetupError(ValueError):
    """Fixed operator-facing explanation, never a raw environment or credential value."""


def run(argv: list[str]) -> None:
    # All programs are the selected Python interpreter or its locally created environment.
    subprocess.run(argv, check=True, timeout=240)  # noqa: S603 # nosec B603


def check_directory(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise SetupError("Installation paths must not be symlinks or junctions")
    for parent in path.parents:
        if parent.is_symlink() or parent.is_junction():
            raise SetupError("Installation parents must not be symlinks or junctions")


def verified_bundle(bundle: Path) -> dict[str, str]:
    manifest = json.loads((bundle / "SHA256SUMS.json").read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("identity") != IDENTITY
        or not isinstance(manifest.get("files"), dict)
    ):
        raise SetupError("Not a Zyntrava desktop bundle")
    files = manifest["files"]
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise SetupError("Invalid bundle manifest entries")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise SetupError("Invalid bundle member path")
        path = bundle / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve().parent not in {bundle.resolve(), (bundle / "wheelhouse").resolve()}
        ):
            raise SetupError("Invalid bundle member")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != expected:
            raise SetupError("Bundle checksum mismatch; do not install")
    if "requirements.txt" not in files or not any(
        n.startswith("wheelhouse/zyntrava_shield-") for n in files
    ):
        raise SetupError("Required installer inputs are missing")
    return files


def install(bundle: Path, target: Path) -> None:
    if os.name != "nt" or sys.version_info[:2] != (3, 13):
        raise SetupError("Use Windows and Python 3.13 with Tcl/Tk")
    check_directory(target)
    verified_bundle(bundle)
    if target.exists():
        raise SetupError(
            "Target already exists. Choose a new empty path; upgrades are not supported"
        )
    run([sys.executable, "-c", "import tkinter as t; r=t.Tk(); r.withdraw(); r.destroy()"])
    target.mkdir(parents=True, exist_ok=False)
    environment = target / "environment"
    # Record ownership even on partial failure so uninstall can remove only our environment.
    (target / "installation.json").write_text(
        json.dumps(
            {"identity": IDENTITY, "root": str(target.resolve()), "status": "installing"}, indent=2
        ),
        encoding="utf-8",
    )
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / "Scripts/python.exe"
    run(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--only-binary=:all:",
            "--find-links",
            str(bundle / "wheelhouse"),
            "--require-hashes",
            "-r",
            str(bundle / "requirements.txt"),
        ]
    )
    run([str(python), "-m", "pip", "check"])
    run([str(python), "-m", "zyntrava", "sdk-demo"])
    # Batch uses its own absolute directory; no arbitrary cwd/PATH Python discovery.
    (target / "Start Zyntrava.cmd").write_text(
        '@echo off\r\n"%~dp0environment\\Scripts\\python.exe" -m zyntrava desktop '
        '--state "%~dp0state"\r\nif errorlevel 1 pause\r\n',
        encoding="ascii",
    )
    (target / "installation.json").write_text(
        json.dumps(
            {"identity": IDENTITY, "root": str(target.resolve()), "status": "installed"}, indent=2
        ),
        encoding="utf-8",
    )
    print("Installed. Open 'Start Zyntrava.cmd'. No model or credentials installed.")


def uninstall(target: Path) -> None:
    check_directory(target)
    marker = target / "installation.json"
    data = json.loads(marker.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("identity") != IDENTITY
        or data.get("root") != str(target.resolve())
    ):
        raise SetupError("Uninstall requires the matching installation ownership marker")
    environment = target / "environment"
    check_directory(environment)
    if environment.resolve().parent != target.resolve():
        raise SetupError("Environment is outside the installation root")
    # No recursive removal of the install root or user state. Paths verified above.
    if environment.exists():
        shutil.rmtree(environment)
    (target / "Start Zyntrava.cmd").unlink(missing_ok=True)
    marker.unlink()
    print(
        "Uninstalled runtime and launcher. State/audits retained; remove them manually if desired."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    try:
        target = args.target.absolute()
        if args.uninstall:
            uninstall(target)
        else:
            install(Path(__file__).resolve().parent, target)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # Avoid echoing environment variables, pip configuration or credentials.
        print(
            f"Setup stopped ({type(exc).__name__}). Check Python/Tk, bundle hashes, permissions "
            "and whether the target already exists. No host security settings were changed.",
            file=sys.stderr,
        )
        if isinstance(exc, SetupError):
            print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
