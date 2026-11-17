"""Trusted fixed-function release, never model-authored redaction or formatting."""

import json
from typing import Literal

from pydantic import Field

from zyntrava.json_input import strict_json
from zyntrava.models import StrictModel


class CountRecord(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,32}$")
    value: str = Field(max_length=512)


class CountDocument(StrictModel):
    schema_id: Literal["zyntrava.records.v1"] = Field(alias="schema")
    records: tuple[CountRecord, ...] = Field(max_length=128)


def record_count(text: str, limit: int) -> str:
    document = CountDocument.model_validate_json(json.dumps(strict_json(text)))
    if not 0 <= len(document.records) <= limit <= 128:
        raise ValueError("record count exceeds the operator's release budget")
    return json.dumps(
        {"schema": "zyntrava.record-count.v1", "record_count": len(document.records)},
        sort_keys=True,
        separators=(",", ":"),
    )
