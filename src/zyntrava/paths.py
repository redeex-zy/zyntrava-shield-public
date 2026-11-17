"""Portable path grammar for dedicated, operator-owned synthetic workspaces."""

import os
import re
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def path_parts(value: str) -> tuple[str, ...]:
    parts = value.split("/")
    if any(not p or p in {".", ".."} or p.endswith((".", " ")) for p in parts):
        raise ValueError("non-canonical relative path")
    for part in parts:
        if (
            not re.fullmatch(r"[A-Za-z0-9_ .-]+", part)
            or part.split(".")[0].rstrip(" ").upper() in _RESERVED
        ):
            raise ValueError("unsupported path component")
    return tuple(parts)


def within(prefix: str, path: str) -> bool:
    # Case-folding intentionally uses Windows-compatible semantics on every OS.
    root, target = path_parts(prefix), path_parts(path)
    return tuple(p.casefold() for p in target[: len(root)]) == tuple(p.casefold() for p in root)


def safe_path(root: Path, value: str) -> Path:
    parts = path_parts(value)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("linked path rejected")
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("reparse point rejected")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError("multiply linked file rejected")
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ValueError("special file rejected")
    resolved = current.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("outside workspace")
    return resolved


@contextmanager
def workspace_file(root: Path, value: str, *, write: bool = False) -> Iterator[BinaryIO]:
    """POSIX handle-relative walk. Windows retains the documented trusted-host boundary."""
    checked = safe_path(root, value)
    directories: list[int] = []
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY
        if os.name == "posix":
            posix_flags = vars(os)
            nofollow = int(posix_flags["O_NOFOLLOW"])
            directory_flag = int(posix_flags["O_DIRECTORY"])
            flags |= nofollow | int(posix_flags["O_CLOEXEC"])
            # A raced-in FIFO must not block before fstat rejects non-regular files.
            if not write:
                flags |= int(posix_flags["O_NONBLOCK"])
            parent = os.open(root, os.O_RDONLY | directory_flag | nofollow)
            directories.append(parent)
            parts = path_parts(value)
            for component in parts[:-1]:
                parent = os.open(component, os.O_RDONLY | directory_flag | nofollow, dir_fd=parent)
                directories.append(parent)
            fd = os.open(parts[-1], flags, 0o600, dir_fd=parent)
        else:
            fd = os.open(checked, flags | int(vars(os).get("O_BINARY", 0)), 0o600)
        with os.fdopen(fd, "wb" if write else "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise ValueError("non-regular or multiply linked opened file")
            if os.name != "posix":
                current = safe_path(root, value).stat()
                if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                    raise ValueError("file identity changed during open")
            yield handle
    finally:
        for directory in reversed(directories):
            os.close(directory)
