"""Bounded real-model tool loop for synthetic research, not a general agent adapter."""

import json
from collections.abc import Callable
from typing import Any

import httpx

from zyntrava.json_input import strict_json
from zyntrava.local_model import LocalRuntime


def interact(
    runtime: LocalRuntime,
    prompt: str,
    tools: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], str],
    *,
    seed: int,
    initial_history: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "Use the available tools to complete the user's task."},
        {"role": "user", "content": prompt},
    ]
    if initial_history is not None:
        serialized = json.dumps(initial_history)
        if len(initial_history) > 32 or len(serialized) > 32768:
            raise ValueError("historical prefix exceeds research budget")
        messages = strict_json(serialized)
    with httpx.Client(trust_env=False, timeout=90) as client:
        for _ in range(8):
            response = client.post(
                runtime.base_url + "/chat/completions",
                headers={"Authorization": f"Bearer {runtime.token}"},
                json={
                    "model": runtime.config["model_id"],
                    "messages": messages,
                    "tools": tools,
                    "temperature": 0.2,
                    "seed": seed,
                    "max_tokens": 512,
                    "parallel_tool_calls": False,
                },
            )
            response.raise_for_status()
            item = response.json()["choices"][0]["message"]
            message = {key: item[key] for key in ("role", "content", "tool_calls") if key in item}
            messages.append(message)
            calls = item.get("tool_calls", [])
            if not calls:
                return item.get("content") or "", messages
            if len(calls) > 4:
                raise ValueError("model exceeded per-turn tool budget")
            for call in calls:
                arguments = strict_json(call["function"]["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
                output = dispatch(call["function"]["name"], arguments)
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
    raise RuntimeError("model exceeded bounded research loop")
