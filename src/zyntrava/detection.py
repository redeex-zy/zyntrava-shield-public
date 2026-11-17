"""Interpretable observations, independent of the authorization verdict."""

import re
import unicodedata
from typing import Literal

from zyntrava.models import Evidence

_INSTRUCTION_PATTERNS = (
    ("instruction_override", r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions\b"),
    (
        "permission_override",
        r"\b(?:disable|bypass|override)\s+(?:the\s+)?(?:policy|permissions|security)\b",
    ),
    ("tool_manipulation", r"\b(?:send|upload|exfiltrate)\b.{0,80}\b(?:secret|credential|token)\b"),
)
_SECRET_PATTERNS = (
    ("synthetic_credential", r"\bZYN_TEST_SECRET_[A-Za-z0-9_-]{6,}\b"),
    ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ("credential_assignment", r"\b(?:api[_-]?key|password|access[_-]?token)\s*[:=]\s*\S{8,}"),
)


def secrets_in(text: str) -> tuple[Evidence, ...]:
    normalized = unicodedata.normalize("NFKC", text)
    return tuple(
        Evidence(
            category="sensitive_information",
            rule=name,
            detail="A credential-shaped value was found; its value is omitted.",
        )
        for name, pattern in _SECRET_PATTERNS
        if re.search(pattern, normalized, flags=re.IGNORECASE)
    )


def instructions_in(text: str, source: Literal["user", "tool"]) -> tuple[Evidence, ...]:
    normalized = unicodedata.normalize("NFKC", text)
    return tuple(
        Evidence(
            category="direct_prompt_injection" if source == "user" else "indirect_prompt_injection",
            rule=name,
            detail="Instruction-like text matched a heuristic; malicious intent is unproven.",
        )
        for name, pattern in _INSTRUCTION_PATTERNS
        if re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
    )
