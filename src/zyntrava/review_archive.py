"""Standalone standard-library reviewer ZIP verifier. Hashes are not authenticity proofs."""

import argparse
import hashlib
import io
import json
import re
import stat
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

MAX_TOTAL = 64 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024


def read_package(package: Path) -> bytes:
    with package.open("rb") as handle:
        payload = handle.read(MAX_TOTAL + 1)
    if len(payload) > MAX_TOTAL:
        raise ValueError("Archive size limit")
    return payload


def verify(package: Path) -> dict[str, Any]:
    return verify_bytes(read_package(package))


def verify_bytes(payload: bytes) -> dict[str, Any]:
    if len(payload) > MAX_TOTAL:
        raise ValueError("Archive size limit")
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        infos = bundle.infolist()
        names = [i.filename for i in infos]
        normalized = [unicodedata.normalize("NFC", n).casefold() for n in names]
        name_set = set(normalized)
        if not 1 <= len(names) <= 5000 or len(set(normalized)) != len(names):
            raise ValueError("Duplicate, aliased or excessive members")
        if sum(i.file_size for i in infos) > MAX_TOTAL:
            raise ValueError("Decompressed size limit")
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)],
        }
        for item in infos:
            parts = item.filename.split("/")
            if len(item.filename) > 240 or len(parts) > 16:
                raise ValueError("Member path budget")
            if (
                "\\" in item.filename
                or ":" in item.filename
                or any(
                    not p
                    or p in {".", "..", ".git", ".state", ".tools"}
                    or p != p.rstrip(" .")
                    or p.split(".")[0].upper() in reserved
                    for p in parts
                )
                or item.filename.endswith((".gguf", ".sqlite3", ".env"))
            ):
                raise ValueError("Unsafe archive member")
            if item.file_size > MAX_FILE or item.flag_bits & 1:
                raise ValueError("Encrypted or oversized member")
            if stat.S_IFMT(item.external_attr >> 16) not in {0, stat.S_IFREG}:
                raise ValueError("Non-regular member")
            if any(
                unicodedata.normalize("NFC", "/".join(parts[:i])).casefold() in name_set
                for i in range(1, len(parts))
            ):
                raise ValueError("File/directory collision")
        metadata = json.loads(bundle.read("REVIEW-PACKAGE.json"))
        if not isinstance(metadata, dict):
            raise ValueError("Manifest object required")
        if metadata.get("schema") != "zyntrava.review091.v1":
            raise ValueError("Unsupported manifest")
        index = metadata["files"]
        if len(index) != len(names) - 1 or {r["path"] for r in index} != set(names) - {
            "REVIEW-PACKAGE.json"
        }:
            raise ValueError("Inventory mismatch")
        for row in index:
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ValueError("Invalid checksum")
            data = bundle.read(row["path"])
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("Checksum mismatch")
        return metadata


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("package", type=Path)
    cli.add_argument("--extract", type=Path)
    args = cli.parse_args()
    payload = read_package(args.package)
    metadata = verify_bytes(payload)
    if args.extract:
        # Extract exactly the bytes that were verified, never re-open a mutable pathname.
        args.extract.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            for name in bundle.namelist():
                target = args.extract.joinpath(*name.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(bundle.read(name))
    print("PASS: bounded names, CRC reads, complete inventory and SHA-256 checks")
    print("Source revision:", metadata["source_revision"])
    print("Archive SHA256:", hashlib.sha256(payload).hexdigest())
    print("Unsigned package; independent testing is still required.")


if __name__ == "__main__":
    main()
