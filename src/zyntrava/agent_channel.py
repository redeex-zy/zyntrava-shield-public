"""Bounded research IPC: the trusted parent owns history and model proposals.

The restricted agent may select only a pending call ID from an actual provider
response. Task/session objects and operator recovery methods never cross IPC.
This binds provenance; the broker remains responsible for authorization.
"""

import json
from collections.abc import Callable
from typing import Any

from zyntrava.json_input import strict_json

Generate = Callable[[list[dict[str, Any]]], dict[str, Any]]
Dispatch = Callable[[str, dict[str, Any]], str]


class AgentChannel:
    def __init__(self, prompt: str, generate: Generate, dispatch: Dispatch) -> None:
        if len(prompt) > 16384:
            raise ValueError("prompt budget exceeded")
        self.generate, self.dispatch = generate, dispatch
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": "Use the available tools to complete the user's task."},
            {"role": "user", "content": prompt},
        ]
        self.pending: dict[str, tuple[str, dict[str, Any]]] = {}
        self.seen: set[str] = set()
        self.turns = self.calls = 0
        self.done = False
        self.answer: str | None = None

    def respond(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.done:
            raise ValueError("channel terminated")
        operation = request.get("op")
        if operation == "model" and set(request) == {"op"}:
            if self.pending or self.answer is not None or self.turns >= 8:
                raise ValueError("invalid model transition")
            self.turns += 1
            # Copy before passing to the trusted provider callback.
            item = self.generate(strict_json(json.dumps(self.messages)))
            if item.get("role") != "assistant" or len(json.dumps(item)) > 65536:
                raise ValueError("invalid provider response")
            calls = item.get("tool_calls") or []
            if not isinstance(calls, list) or len(calls) > 4:
                raise ValueError("invalid provider tool budget")
            selected: dict[str, Any] = {
                k: item[k] for k in ("role", "content", "tool_calls") if k in item
            }
            pending: dict[str, tuple[str, dict[str, Any]]] = {}
            for call in calls:
                identity, function = call["id"], call["function"]
                if (
                    not isinstance(identity, str)
                    or not 1 <= len(identity) <= 128
                    or identity in self.seen
                    or identity in pending
                    or call.get("type") != "function"
                    or not isinstance(function["name"], str)
                    or not 1 <= len(function["name"]) <= 64
                ):
                    raise ValueError("invalid provider call identity")
                arguments = strict_json(function["arguments"])
                if not isinstance(arguments, dict):
                    raise ValueError("provider arguments must be an object")
                pending[identity] = function["name"], arguments
            if self.calls + len(pending) > 12:
                raise ValueError("total tool budget exceeded")
            self.pending = pending
            self.seen.update(pending)
            self.messages.append(selected)
            if not calls:
                content = item.get("content") or ""
                if not isinstance(content, str):
                    raise ValueError("invalid final content")
                self.answer = content
            return selected
        if operation == "tool" and set(request) == {"op", "id"}:
            identity = request["id"]
            if not isinstance(identity, str) or identity not in self.pending:
                raise ValueError("tool proposal not pending")
            name, arguments = self.pending.pop(identity)
            self.calls += 1
            try:
                output = self.dispatch(name, arguments)
                if not isinstance(output, str) or len(output.encode()) > 60000:
                    raise ValueError("tool response budget exceeded")
            except Exception:
                self.done = True  # Never retry an ambiguous dispatch from a failed IPC call.
                raise
            self.messages.append({"role": "tool", "tool_call_id": identity, "content": output})
            return {"output": output}
        if operation == "answer" and set(request) == {"op"}:
            if self.pending or self.answer is None:
                raise ValueError("final answer not generated")
            self.done = True
            return {"accepted": True}
        raise ValueError("unregistered channel operation or fields")
