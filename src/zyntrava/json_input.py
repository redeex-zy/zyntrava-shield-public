"""One JSON interpretation: no duplicate keys, non-finite numbers or deep trees."""

import json
import math
from typing import Any


def strict_json(value: str | bytes, *, max_items: int = 4096) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = item
        return result

    def constant(value: str) -> None:
        raise ValueError("non-finite JSON number")

    try:
        parsed = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
        pending = [(parsed, 0)]
        inspected = 0
        while pending:
            item, depth = pending.pop()
            inspected += 1
            if depth > 32 or inspected > max_items:
                raise ValueError("JSON structure budget exceeded")
            if isinstance(item, dict):
                for key, child in item.items():
                    key.encode("utf-8")
                    pending.append((child, depth + 1))
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
            elif isinstance(item, str):
                item.encode("utf-8")
            elif isinstance(item, float) and not math.isfinite(item):
                raise ValueError("non-finite JSON number")
        return parsed
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("invalid JSON encoding or structure") from exc
