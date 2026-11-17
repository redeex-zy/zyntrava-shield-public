import pytest

from zyntrava.lab.preview import preview_fixture

IDENTITY = "external-isolated-20261029T000000Z-12345678"


def test_preview_fixture_validates_owned_regular_payload(tmp_path):
    inputs = tmp_path / (IDENTITY + "-inputs")
    inputs.mkdir()
    fixture = inputs / "public.pdf"
    fixture.write_bytes(b"owned synthetic fixture")
    assert preview_fixture(tmp_path, IDENTITY, "public.pdf") == fixture.resolve()


@pytest.mark.parametrize("filename", ["../private.txt", "/private.txt", "public.svg"])
def test_untrusted_trace_cannot_copy_outside_fixture_directory(tmp_path, filename):
    (tmp_path / "private.txt").write_text("SYNTHETIC_TEST_CANARY")
    with pytest.raises(ValueError):
        preview_fixture(tmp_path, IDENTITY, filename)
