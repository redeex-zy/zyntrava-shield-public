"""Closed schemas shared by the engine, broker and local API."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

ToolName = Literal["read_file", "write_file", "post_message", "fetch_page", "export_count"]
Effect = Literal["allow", "deny", "approve"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ToolRequest(StrictModel):
    tool: str = Field(min_length=1, max_length=64)
    arguments: dict[str, JsonValue]

    @model_validator(mode="after")
    def bounded(self) -> "ToolRequest":
        if len(json.dumps(self.arguments, ensure_ascii=True)) > 32768:
            raise ValueError("tool arguments exceed the 32 KiB serialized limit")
        return self


class ReadArgs(StrictModel):
    path: str = Field(min_length=1, max_length=512)


class WriteArgs(ReadArgs):
    content: str = Field(max_length=16384)


class FetchArgs(StrictModel):
    url: str = Field(min_length=1, max_length=2048)


class PostArgs(FetchArgs):
    body: str = Field(max_length=16384)


class CountArgs(ReadArgs):
    url: str = Field(min_length=1, max_length=2048)


Arguments = ReadArgs | WriteArgs | FetchArgs | PostArgs | CountArgs


class Evidence(StrictModel):
    category: str
    rule: str
    detail: str  # Fixed explanation; never include the matched secret or raw input.


class Decision(StrictModel):
    effect: Effect
    policy_digest: str
    rule_ids: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()


class Outcome(StrictModel):
    """Execution certainty, separate from authorization and business-task success.

    not_run: dispatch did not start (including pending approval).
    failed: the trusted executor establishes failure before any effect.
    succeeded: the supported tool completed; this is not a business receipt.
    unknown: dispatch may have produced an effect; never automatically retry.
    """

    event_id: str
    status: Literal["allowed", "blocked", "sent_for_approval"]
    execution: Literal["not_run", "succeeded", "failed", "unknown"]
    decision: Decision
    output: str | None = None
    approval_id: str | None = None
