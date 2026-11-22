"""The only executable tools. No general network or command execution."""

import http.client
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import ValidationError

from zyntrava.models import (
    Arguments,
    CountArgs,
    FetchArgs,
    PostArgs,
    ReadArgs,
    ToolName,
    ToolRequest,
    WriteArgs,
)
from zyntrava.paths import safe_path, workspace_file
from zyntrava.policy import validate_destination
from zyntrava.projectors import record_count

MAX_OUTPUT_BYTES = 32768


class BeforeEffectError(ValueError):
    """Only trusted executor code may assert that no effect could have occurred."""


def parse_action(request: ToolRequest) -> tuple[ToolName, Arguments]:
    match request.tool:
        case "read_file":
            return "read_file", ReadArgs.model_validate(request.arguments)
        case "write_file":
            return "write_file", WriteArgs.model_validate(request.arguments)
        case "post_message":
            return "post_message", PostArgs.model_validate(request.arguments)
        case "fetch_page":
            return "fetch_page", FetchArgs.model_validate(request.arguments)
        case "export_count":
            return "export_count", CountArgs.model_validate(request.arguments)
        case _:
            raise ValueError("unknown tool")


class LabTools:
    def __init__(self, root: Path) -> None:
        if not root.is_dir() or root.is_symlink():
            raise ValueError("workspace must be an existing dedicated directory")
        self.root = root.resolve()

    def validate(self, args: Arguments) -> None:
        if isinstance(args, CountArgs):
            validate_destination(args.url)
        if isinstance(args, FetchArgs):
            validate_destination(args.url)
        else:
            safe_path(self.root, args.path)

    def execute(self, tool: ToolName, args: Arguments, *, count_limit: int | None = None) -> str:
        try:
            self.validate(args)  # Recheck the exact object passed to the side effect.
        except (ValueError, OSError) as exc:
            raise BeforeEffectError("Resource validation failed before dispatch.") from exc
        if tool == "read_file" and isinstance(args, ReadArgs) and not isinstance(args, WriteArgs):
            if isinstance(args, CountArgs):
                raise ValueError("tool/argument mismatch")
            try:
                with workspace_file(self.root, args.path) as handle:
                    data = handle.read(MAX_OUTPUT_BYTES + 1)
                if len(data) > MAX_OUTPUT_BYTES:
                    raise ValueError("file exceeds output limit")
                return data.decode("utf-8")
            except (ValueError, OSError) as exc:
                # No file mutation/network effect or tool output release on this path.
                raise BeforeEffectError("Read failed without releasing output.") from exc
        if tool == "write_file" and isinstance(args, WriteArgs):
            # Exclusive create: no overwrite, no automatically created parent directories.
            try:
                encoded = args.content.encode("utf-8")
            except UnicodeError as exc:
                raise BeforeEffectError("Content encoding failed before creation.") from exc
            try:
                with workspace_file(self.root, args.path, write=True) as handle:
                    handle.write(encoded)
            except FileExistsError as exc:
                # O_EXCL refuses the existing file; it is never opened for mutation.
                raise BeforeEffectError("Exclusive creation refused an existing file.") from exc
            return "File created."
        if tool == "export_count" and isinstance(args, CountArgs):
            if count_limit is None:
                raise ValueError("operator release budget required")
            try:
                with workspace_file(self.root, args.path) as handle:
                    data = handle.read(MAX_OUTPUT_BYTES + 1)
                if len(data) > MAX_OUTPUT_BYTES:
                    raise ValueError("projector source exceeds input limit")
                payload = record_count(data.decode("utf-8"), count_limit)
            except (ValueError, OSError) as exc:
                raise BeforeEffectError("Projection failed before network dispatch.") from exc
            self.execute("post_message", PostArgs(url=args.url, body=payload))
            return payload
        if tool in {"post_message", "fetch_page"} and isinstance(args, FetchArgs):
            if (tool == "post_message") != isinstance(args, PostArgs):
                raise ValueError("network tool/argument mismatch")
            parsed = urlsplit(args.url)
            try:
                body = args.body.encode("utf-8") if isinstance(args, PostArgs) else None
            except UnicodeError as exc:
                raise BeforeEffectError("Body encoding failed before dispatch.") from exc
            conn = http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=2)
            try:
                try:
                    conn.connect()
                except OSError as exc:
                    raise BeforeEffectError("Connection failed before HTTP dispatch.") from exc
                conn.request(
                    "POST" if tool == "post_message" else "GET",
                    parsed.path,
                    body=body,
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                )
                response = conn.getresponse()
                data = response.read(MAX_OUTPUT_BYTES + 1)
                if 300 <= response.status < 400:
                    raise ValueError("redirects are never followed")
                if not 200 <= response.status < 300 or len(data) > MAX_OUTPUT_BYTES:
                    raise ValueError("invalid or oversized lab response")
                return data.decode("utf-8")
            finally:
                conn.close()
        raise ValueError("tool/argument mismatch")


ACTION_ERRORS = (ValueError, OSError, ValidationError, http.client.HTTPException)
