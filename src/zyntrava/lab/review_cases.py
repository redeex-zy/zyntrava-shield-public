"""Untrusted reviewer content changes fixtures and observer goals, never permissions."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from zyntrava.json_input import strict_json


class ReviewCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    channel: Literal["file", "web"]
    attack: bool
    content: str = Field(max_length=16384)
    goal: Literal["none", "private-read", "private-write", "redirect", "extra-field"] = "none"


class ReviewCases(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_id: Literal["zyntrava.review091.cases.v1", "zyntrava.agent09.cases.v1"] = Field(
        alias="schema"
    )
    authorship: str = Field(
        default="Reviewer-supplied; authorship not independently verified", max_length=500
    )
    cases: list[ReviewCase] = Field(min_length=1, max_length=50)


def load_case_data(path: Path) -> tuple[bytes, list[dict[str, object]]]:
    with path.open("rb") as handle:
        data = handle.read(1048577)
    if len(data) > 1048576:
        raise ValueError("review case file exceeds 1 MiB")
    parsed = ReviewCases.model_validate(strict_json(data))
    if len({c.id for c in parsed.cases}) != len(parsed.cases):
        raise ValueError("duplicate case identifier")
    return data, [c.model_dump() for c in parsed.cases]


def load_cases(path: Path) -> list[dict[str, object]]:
    return load_case_data(path)[1]
