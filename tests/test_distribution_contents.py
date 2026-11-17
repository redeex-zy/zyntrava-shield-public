import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def test_gitless_source_build_excludes_local_state_and_dependency_trees(tmp_path):
    root = Path(__file__).resolve().parents[1]
    uv = shutil.which("uv") or str(
        root
        / (".bootstrap/Scripts/uv.exe" if sys.platform == "win32" else ".tools/linux-uv/bin/uv")
    )
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "NOTICE", "uv.lock"):
        shutil.copyfile(root / name, source / name)
    for name in ("scripts/hatch_build.py", "src/zyntrava/__init__.py"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, path)
    for name in (
        ".state/preview-env/synthetic-private.txt",
        "apps/dashboard/node_modules/synthetic-dependency.txt",
        "apps/dashboard/out/synthetic-bundle.txt",
        "artifacts/synthetic-trace.txt",
        ".env",
        "src/zyntrava/__pycache__/synthetic.pyc",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SYNTHETIC_DISTRIBUTION_EXCLUSION_MARKER", encoding="utf-8")
    output = tmp_path / "builds"
    result = subprocess.run(  # noqa: S603 -- fixed build command on owned synthetic tree.
        [uv, "build", "--sdist", "--python", sys.executable, "--out-dir", str(output)],
        cwd=source,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, (result.stdout + result.stderr).decode("utf-8", "replace")
    with tarfile.open(next(output.glob("*.tar.gz"))) as archive:
        names = archive.getnames()
        assert any(n.endswith("src/zyntrava/__init__.py") for n in names)
        assert not any(
            part in n.split("/")
            for n in names
            for part in (".state", "node_modules", "artifacts", ".env", "__pycache__")
        )
        assert not any(
            b"SYNTHETIC_DISTRIBUTION_EXCLUSION_MARKER" in stream.read()
            for member in archive.getmembers()
            if member.isfile() and (stream := archive.extractfile(member)) is not None
        )
