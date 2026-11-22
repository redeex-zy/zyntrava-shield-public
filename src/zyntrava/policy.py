"""Small JSON policy: deny > approve > allow > implicit deny."""

import hashlib
import json
import math
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from zyntrava.detection import secrets_in
from zyntrava.json_input import strict_json
from zyntrava.models import (
    Arguments,
    CountArgs,
    Decision,
    Effect,
    Evidence,
    FetchArgs,
    PostArgs,
    ReadArgs,
    StrictModel,
    ToolName,
    WriteArgs,
)
from zyntrava.paths import path_parts, within


def validate_destination(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.port is None
        or not 1024 <= parsed.port <= 65535
        or not parsed.path.startswith("/")
        or any(c in value for c in "\r\n\\%")
    ):
        raise ValueError("only explicit numeric-loopback HTTP lab endpoints are supported")
    if value != f"http://127.0.0.1:{parsed.port}{parsed.path}":
        raise ValueError("non-canonical destination")
    return value


class Rule(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    tool: ToolName
    effect: Effect
    path_prefix: str | None = None
    destination: str | None = None
    # Optional exact scalar fields in a strict JSON POST object (not substring matching).
    body_fields: tuple[tuple[str, str | float], ...] = Field(default=(), max_length=16)
    # Opt-in closed key set. Omit False to preserve historical serialization/digests.
    exact_body_fields: bool = Field(default=False, exclude_if=lambda value: value is False)

    @model_validator(mode="after")
    def scoped(self) -> "Rule":
        if self.exact_body_fields and not self.body_fields:
            raise ValueError("exact body fields requires explicit scalar permissions")
        if self.body_fields:
            if self.tool != "post_message" or self.effect != "allow":
                raise ValueError("body fields are scoped allow permissions for POST only")
            if len({key for key, _ in self.body_fields}) != len(self.body_fields):
                raise ValueError("duplicate body field")
            if any(
                not key or len(key) > 64 or len(str(value)) > 256 for key, value in self.body_fields
            ):
                raise ValueError("body field exceeds scalar scope")
            if any(
                isinstance(value, float) and not math.isfinite(value)
                for _, value in self.body_fields
            ):
                raise ValueError("body field must be finite")
        if self.tool == "export_count":
            raise ValueError(
                "export_count requires an explicit release rule, not a broad tool rule"
            )
        if self.tool in {"post_message", "fetch_page"}:
            if self.destination is None or self.path_prefix is not None:
                raise ValueError("network rules require only a destination scope")
            validate_destination(self.destination)
        else:
            if self.path_prefix is None or self.destination is not None:
                raise ValueError("file rules require only a path scope")
            path_parts(self.path_prefix)
        return self


class ReleaseRule(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    source: str = Field(min_length=1, max_length=512)
    destination: str
    projector: Literal["record_count_v1"] = "record_count_v1"
    max_records: int = Field(default=32, ge=0, le=128)
    max_releases: int = Field(default=1, ge=1, le=128)

    @model_validator(mode="after")
    def valid_scope(self) -> "ReleaseRule":
        path_parts(self.source)
        validate_destination(self.destination)
        return self


class Policy(StrictModel):
    version: int = Field(ge=1, le=1)
    name: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    rules: tuple[Rule, ...] = Field(max_length=128)
    sensitive_roots: tuple[str, ...] = ("sensitive",)
    release_rules: tuple[ReleaseRule, ...] = Field(default=(), max_length=16)
    # Omit legacy defaults so existing policy JSON/digests remain byte-compatible.
    profile: Literal["legacy", "strict"] = Field(
        default="legacy", exclude_if=lambda value: value == "legacy"
    )
    sensitive_reads_acknowledged: bool = Field(
        default=False, exclude_if=lambda value: value is False
    )

    @field_validator("sensitive_roots")
    @classmethod
    def valid_roots(cls, roots: tuple[str, ...]) -> tuple[str, ...]:
        for root in roots:
            path_parts(root)
        return roots

    @model_validator(mode="after")
    def unique_rules(self) -> "Policy":
        identifiers = [r.id for r in self.rules] + [r.id for r in self.release_rules]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate rule identifiers")
        scopes = [(r.source, r.destination) for r in self.release_rules]
        if len(set(scopes)) != len(scopes):
            raise ValueError("duplicate release scopes")
        if any(
            not any(within(root, rule.source) for root in self.sensitive_roots)
            for rule in self.release_rules
        ):
            raise ValueError("release sources must be explicitly classified as sensitive")
        if self.profile == "strict":
            hazards = [e.rule for e in self.diagnostics() if e.category == "policy_error"]
            if hazards:
                raise ValueError("Strict policy configuration rejected: " + ", ".join(hazards))
        return self

    def diagnostics(self) -> tuple[Evidence, ...]:
        """Fixed configuration diagnostics only; never inspect data or infer model intent."""
        result = []
        severity = "policy_error" if self.profile == "strict" else "policy_warning"
        if not self.sensitive_roots:
            result.append(
                Evidence(
                    category=severity,
                    rule="empty_sensitive_roots",
                    detail="Source classification absent; credential regexes are incomplete.",
                )
            )
        for rule in self.rules:
            if rule.tool == "post_message" and rule.effect != "deny":
                if not rule.body_fields or not rule.exact_body_fields:
                    result.append(
                        Evidence(
                            category=severity,
                            rule="open_message_schema",
                            detail="Strict outgoing permissions require explicit exact fields.",
                        )
                    )
            if rule.tool == "read_file" and rule.effect == "allow" and rule.path_prefix:
                if any(
                    within(root, rule.path_prefix) or within(rule.path_prefix, root)
                    for root in self.sensitive_roots
                ):
                    result.append(
                        Evidence(
                            category="policy_warning"
                            if self.sensitive_reads_acknowledged
                            else severity,
                            rule="classified_read_permission",
                            detail="Read scope overlaps classified data; operator review required.",
                        )
                    )
        if self.release_rules and self.profile == "strict":
            result.append(
                Evidence(
                    category="policy_error",
                    rule="strict_count_release_unsupported",
                    detail="Strict message schemas do not support legacy count-send permissions.",
                )
            )
        return tuple(result)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    @classmethod
    def load(cls, path: Path) -> "Policy":
        return cls.model_validate_json(json.dumps(strict_json(path.read_bytes())))

    def evaluate(
        self, tool: ToolName, args: Arguments, *, sensitive_read: bool, full: bool = True
    ) -> Decision:
        evidence: list[Evidence] = []
        if tool == "export_count" and isinstance(args, CountArgs):
            rule = next(
                (
                    r
                    for r in self.release_rules
                    if r.source == args.path and r.destination == args.url
                ),
                None,
            )
            read = self.evaluate(
                "read_file", ReadArgs(path=args.path), sensitive_read=sensitive_read, full=full
            )
            send = self.evaluate(
                "post_message", PostArgs(url=args.url, body=""), sensitive_read=False, full=False
            )
            if rule is None or read.effect != "allow" or send.effect != "allow":
                return self.deny(
                    "unauthorized_release",
                    "release_scope",
                    "Exact release grant and existing read/send permissions required.",
                )
            return Decision(
                effect="allow",
                policy_digest=self.digest,
                rule_ids=(rule.id, *read.rule_ids, *send.rule_ids),
            )
        if isinstance(args, FetchArgs):
            try:
                validate_destination(args.url)
            except ValueError:
                return self.deny(
                    "suspicious_destination",
                    "destination_scope",
                    "Destination is outside the numeric-loopback lab boundary.",
                )
        if tool in {"post_message", "write_file"}:
            payload = (
                args.body
                if isinstance(args, PostArgs)
                else (args.content if isinstance(args, WriteArgs) else "")
            )
            evidence.extend(secrets_in(payload))
            if evidence:
                return Decision(effect="deny", policy_digest=self.digest, evidence=tuple(evidence))
            if full and sensitive_read:
                return self.deny(
                    "sensitive_data_exfiltration",
                    "session_sensitive_read",
                    "A prior sensitive read prohibits all session output sinks.",
                )
        matches = tuple(
            r
            for r in self.rules
            if r.tool == tool
            and (
                r.destination == args.url
                if isinstance(args, FetchArgs)
                else r.path_prefix is not None and within(r.path_prefix, args.path)
            )
            and self._body_matches(r, args)
        )
        for effect in ("deny", "approve", "allow"):
            selected = tuple(r.id for r in matches if r.effect == effect)
            if selected:
                return Decision(effect=effect, policy_digest=self.digest, rule_ids=selected)
        return self.deny("unauthorized_action", "default_deny", "No scoped permission matched.")

    @staticmethod
    def _body_matches(rule: Rule, args: Arguments) -> bool:
        if not rule.body_fields:
            return True
        if not isinstance(args, PostArgs):
            return False
        try:
            body = strict_json(args.body.encode())
        except (ValueError, UnicodeError):
            return False
        if not isinstance(body, dict):
            return False
        if rule.exact_body_fields and set(body) != {key for key, _ in rule.body_fields}:
            return False
        return all(
            key in body and type(body[key]) is type(value) and body[key] == value
            for key, value in rule.body_fields
        )

    def count_limit(self, args: CountArgs) -> int:
        return next(
            r.max_records
            for r in self.release_rules
            if r.source == args.path and r.destination == args.url
        )

    def release_budget(self, args: CountArgs) -> int:
        return next(
            r.max_releases
            for r in self.release_rules
            if r.source == args.path and r.destination == args.url
        )

    def deny(self, category: str, rule: str, detail: str) -> Decision:
        return Decision(
            effect="deny",
            policy_digest=self.digest,
            evidence=(Evidence(category=category, rule=rule, detail=detail),),
        )


def default_policy(
    endpoint: str = "http://127.0.0.1:8766/collect", *, page: str | None = None
) -> Policy:
    policy = Policy.model_validate_json(
        json.dumps(
            {
                "version": 1,
                "name": "local-lab-v1",
                "sensitive_roots": ["sensitive"],
                "rules": [
                    {
                        "id": "deny-private-read",
                        "tool": "read_file",
                        "effect": "deny",
                        "path_prefix": "private",
                    },
                    {
                        "id": "read-public",
                        "tool": "read_file",
                        "effect": "allow",
                        "path_prefix": "public",
                    },
                    {
                        "id": "read-sensitive",
                        "tool": "read_file",
                        "effect": "allow",
                        "path_prefix": "sensitive",
                    },
                    {
                        "id": "approve-reports",
                        "tool": "write_file",
                        "effect": "approve",
                        "path_prefix": "reports",
                    },
                    {
                        "id": "send-lab",
                        "tool": "post_message",
                        "effect": "allow",
                        "destination": endpoint,
                    },
                ],
            }
        )
    )
    if page is not None:
        return policy.model_copy(
            update={
                "rules": (
                    *policy.rules,
                    Rule(id="read-lab-page", tool="fetch_page", effect="allow", destination=page),
                )
            }
        )
    return policy


def strict_status_policy(endpoint: str) -> Policy:
    """Opt-in fixed status workflow; does not change default_policy or legacy permissions."""
    return Policy(
        version=1,
        name="strict-local-status",
        profile="strict",
        sensitive_roots=("sensitive",),
        rules=(
            Rule(
                id="read-status", tool="read_file", effect="allow", path_prefix="public/status.txt"
            ),
            Rule(
                id="send-status",
                tool="post_message",
                effect="allow",
                destination=endpoint,
                body_fields=(("status", "ready"),),
                exact_body_fields=True,
            ),
        ),
    )
