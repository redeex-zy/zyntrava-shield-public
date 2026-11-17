import hashlib
import io
import json
import zipfile

import pytest

from zyntrava.review_archive import verify_bytes


def archive(files, inventory=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        for name, data in files:
            bundle.writestr(name, data)
        bundle.writestr(
            "REVIEW-PACKAGE.json",
            json.dumps(
                {
                    "schema": "zyntrava.review091.v1",
                    "source_revision": "synthetic",
                    "files": inventory
                    or [{"path": n, "sha256": hashlib.sha256(d).hexdigest()} for n, d in files],
                }
            ),
        )
    return stream.getvalue()


def test_curated_inventory_and_corruption_detection():
    assert (
        verify_bytes(archive([("source/example.py", b"synthetic")]))["source_revision"]
        == "synthetic"
    )
    bad = archive(
        [("source/example.py", b"changed")], [{"path": "source/example.py", "sha256": "0" * 64}]
    )
    with pytest.raises(ValueError, match="Checksum"):
        verify_bytes(bad)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "source/../../escape",
        "/absolute",
        "source/a:b",
        "source\\escape",
        "source/NUL.txt",
        "source/space. ",
        "source/.git/config",
        "source/private.env",
        "source/model.gguf",
    ],
)
def test_unsafe_members_rejected_before_extraction(name):
    with pytest.raises(ValueError):
        verify_bytes(archive([(name, b"dummy")]))


def test_duplicate_alias_and_file_directory_collisions():
    for names in [["source/A", "source/a"], ["source/a", "source/a/b"]]:
        with pytest.raises(ValueError):
            verify_bytes(archive([(n, b"dummy") for n in names]))
