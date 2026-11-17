"""Experiment configuration is validated before constructing directories or tools."""

from typing import Literal

from pydantic import Field, model_validator

from zyntrava.models import StrictModel, ToolRequest


class Step(ToolRequest):
    unauthorized: bool
    approve: bool = False


class Scenario(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    split: Literal["development", "heldout"]
    malicious: bool
    prompt: str = Field(default="", max_length=32768)
    steps: tuple[Step, ...] = Field(min_length=1, max_length=20)
    category: str = Field(default="legacy", max_length=64)
    rationale: str = Field(default="", max_length=512)


class Corpus(StrictModel):
    version: Literal["zyntrava-traces-1", "zyntrava-traces-2"]
    kind: Literal["synthetic-policy-traces-not-model-evaluation"]
    scenarios: tuple[Scenario, ...] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def identifiers_and_splits(self) -> "Corpus":
        if len({s.id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("duplicate scenario identifiers")
        if {s.split for s in self.scenarios} != {"development", "heldout"}:
            raise ValueError("both corpus splits are required")
        return self
