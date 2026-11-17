"""Constrain untrusted trace filenames before copying synthetic preview fixtures."""

import re
from pathlib import Path


def preview_fixture(directory: Path, experiment_id: str, filename: str) -> Path:
    if not re.fullmatch(r"external-isolated-\d{8}T\d{6}Z-[a-f0-9]{8}", experiment_id):
        raise ValueError("unsupported experiment identity")
    if not re.fullmatch(r"[a-z0-9_-]+\.(txt|pdf|html)", filename):
        raise ValueError("unsupported fixture filename")
    base = (directory / (experiment_id + "-inputs")).resolve()
    candidate = base / filename
    if (
        candidate.is_symlink()
        or not candidate.is_file()
        or not candidate.resolve().is_relative_to(base)
    ):
        raise ValueError("fixture must be a regular file within its experiment inputs")
    return candidate
