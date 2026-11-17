"""Frozen v3 contract suite; grading labels never configure enforcement."""

from typing import Literal

from pydantic import Field, model_validator

from zyntrava.models import StrictModel, ToolRequest
from zyntrava.paths import path_parts

Profile = Literal[
    "standard",
    "read_only",
    "deny_network",
    "deny_public",
    "deny_sensitive",
    "report_auto",
    "release_approved",
    "no_send_permission",
]


class Attempt(ToolRequest):
    unauthorized: bool
    expected: Literal["succeeded", "blocked", "failed", "sent_for_approval"]
    approve: bool = False


class Workflow(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    split: Literal["development", "heldout"]
    category: str = Field(max_length=64)
    task_type: Literal["benign", "malicious", "ambiguous"]
    profile: Profile
    document_format: Literal["text", "markdown", "html", "json", "csv", "yaml"] = "text"
    prompt: str = Field(default="", max_length=4096)
    fixtures: dict[str, str] = Field(default_factory=dict, max_length=4)
    steps: tuple[Attempt, ...] = Field(min_length=1, max_length=16)
    rationale: str = Field(max_length=512)

    @model_validator(mode="after")
    def contained_fixtures(self) -> "Workflow":
        for path, text in self.fixtures.items():
            parts = path_parts(path)
            if parts[0] not in {"public", "sensitive", "private"} or len(text) > 40000:
                raise ValueError("fixture outside dedicated synthetic inputs")
        return self


class AdversarialCorpus(StrictModel):
    version: Literal["zyntrava-adversarial-3"]
    kind: Literal["synthetic-adversarial-contracts-not-model-evaluation"]
    design: str
    scenarios: tuple[Workflow, ...] = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def unique(self) -> "AdversarialCorpus":
        if len({r.id for r in self.scenarios}) != len(self.scenarios):
            raise ValueError("duplicate scenario identifiers")
        if {r.split for r in self.scenarios} != {"development", "heldout"}:
            raise ValueError("both splits required")
        return self
