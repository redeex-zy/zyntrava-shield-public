"""Authenticated loopback API. Operator and agent credentials are distinct."""

import asyncio
import hashlib
import hmac
import re
import sqlite3
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from zyntrava import __version__
from zyntrava.broker import Broker
from zyntrava.control import Control, JobRequest, PolicyUpdate, Settings
from zyntrava.json_input import strict_json
from zyntrava.models import StrictModel, ToolRequest


class LocalBoundary:
    def __init__(
        self, app: ASGIApp, authority: str, script_hashes: str = "", body_timeout: float = 5
    ) -> None:
        self.app, self.authority = app, authority
        self.script_hashes = script_hashes
        self.body_timeout = body_timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        single = {b"host", b"origin", b"authorization", b"content-type", b"content-length"}
        if any(sum(name == key for name, _ in scope["headers"]) > 1 for key in single):
            await JSONResponse({"detail": "Ambiguous request headers"}, status_code=400)(
                scope, receive, send
            )
            return
        origin = headers.get(b"origin")
        if headers.get(b"host", b"").decode("latin1") != self.authority or (
            origin is not None and origin.decode("latin1") != f"http://{self.authority}"
        ):
            await JSONResponse({"detail": "Host or origin rejected"}, status_code=403)(
                scope, receive, send
            )
            return
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            if headers.get(b"content-type", b"").split(b";", 1)[0] != b"application/json":
                await JSONResponse({"detail": "application/json required"}, status_code=415)(
                    scope, receive, send
                )
                return
        # Bound the body before FastAPI parses it. Raising from receive can be
        # converted by frameworks into a generic 400, losing the size semantics.
        body = bytearray()
        try:
            async with asyncio.timeout(self.body_timeout):
                while True:
                    part = await receive()
                    if part["type"] == "http.disconnect":
                        return
                    body.extend(part.get("body", b""))
                    if len(body) > 65536:
                        await JSONResponse({"detail": "Request exceeds 64 KiB"}, status_code=413)(
                            scope, receive, send
                        )
                        return
                    if not part.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"detail": "Request body deadline exceeded"}, status_code=408)(
                scope, receive, send
            )
            return
        delivered = False
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            try:
                strict_json(bytes(body))
            except ValueError:
                await JSONResponse({"detail": "Invalid or ambiguous JSON"}, status_code=422)(
                    scope, receive, send
                )
                return

        async def bounded_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                csp = "default-src 'none'; frame-ancestors 'none'"
                if scope["path"].startswith("/app"):
                    csp = (
                        f"default-src 'self'; script-src 'self' {self.script_hashes}; "
                        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                        "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; "
                        "base-uri 'none'; form-action 'self'"
                    )
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"content-security-policy", csp.encode()),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-robots-tag", b"noindex, nofollow, noarchive"),
                ]
            await send(message)

        await self.app(scope, bounded_receive, secured_send)


class ApprovalRequest(StrictModel):
    allow: bool


def create_app(
    broker: Broker,
    *,
    admin_token: str,
    agent_token: str,
    authority: str = "127.0.0.1:8765",
    control: Control | None = None,
    dashboard: Path | None = None,
) -> FastAPI:
    if min(len(admin_token), len(agent_token)) < 32 or admin_token == agent_token:
        raise ValueError("distinct credentials of at least 32 characters are required")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if control:
            control.close()

    app = FastAPI(
        title="Zyntrava Shield local API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    hashes = set()
    if dashboard and dashboard.is_dir():
        import base64

        for path in dashboard.rglob("*.html"):
            for script in re.findall(
                r"<script(?:\s[^>]*)?>(.*?)</script>", path.read_text(encoding="utf-8"), re.S
            ):
                if script:
                    hashes.add(
                        "'sha256-"
                        + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                        + "'"
                    )
    app.add_middleware(LocalBoundary, authority=authority, script_hashes=" ".join(sorted(hashes)))

    def role(request: Request) -> str:
        auth = request.headers.get("authorization", "").encode("utf-8")
        if hmac.compare_digest(auth, f"Bearer {admin_token}".encode()):
            return "admin"
        if hmac.compare_digest(auth, f"Bearer {agent_token}".encode()):
            return "agent"
        raise HTTPException(status_code=401, detail="Valid bearer credential required")

    def admin(current: Annotated[str, Depends(role)]) -> None:
        if current != "admin":
            raise HTTPException(status_code=403, detail="Operator credential required")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default validation details can echo submitted secret values.
        return JSONResponse({"detail": "Request does not match the closed schema"}, status_code=422)

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Unknown session, approval, or invalid operation"}, status_code=400
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "release": __version__}

    @app.get("/ready", dependencies=[Depends(admin)])
    def readiness() -> JSONResponse:
        # Readiness is audit readability, not proof of future writes or OS isolation.
        try:
            broker.audit.stats()
        except sqlite3.Error:
            return JSONResponse({"status": "unavailable", "audit": "unreadable"}, status_code=503)
        return JSONResponse({"status": "ready", "audit": "readable", "version": __version__})

    @app.get("/robots.txt", include_in_schema=False)
    def robots() -> PlainTextResponse:
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    agent_session: str | None = None
    agent_session_lock = threading.Lock()

    @app.post("/sessions")
    def session(current: Annotated[str, Depends(role)]) -> dict[str, str]:
        nonlocal agent_session
        if current == "admin":
            return {"session_id": broker.create_session()}
        with agent_session_lock:
            if agent_session is None:
                agent_session = broker.create_session()
            return {"session_id": agent_session}

    @app.post("/sessions/{session_id}/actions")
    def action(
        session_id: str, proposal: ToolRequest, current: Annotated[str, Depends(role)]
    ) -> Any:
        if current == "agent" and session_id != agent_session:
            raise HTTPException(status_code=403, detail="Session outside credential scope")
        return broker.submit(session_id, proposal)

    @app.get("/overview", dependencies=[Depends(admin)])
    def overview() -> dict[str, Any]:
        return control.overview() if control else broker.overview()

    @app.get("/events", dependencies=[Depends(admin)])
    def events(
        limit: int = Query(100, ge=1, le=500),
        status: str | None = Query(None, max_length=32),
        search: str = Query("", max_length=128),
    ) -> list[dict[str, Any]]:
        return broker.audit.events(limit=limit, status=status, search=search)

    @app.get("/policy", dependencies=[Depends(admin)])
    def policy() -> dict[str, Any]:
        return {
            "policy": broker.policy.model_dump(),
            "digest": broker.policy.digest,
            "editing": "operator; optimistic concurrency" if control else "offline-only",
        }

    @app.get("/approvals", dependencies=[Depends(admin)])
    def approvals() -> list[dict[str, Any]]:
        return broker.approvals()

    @app.post("/approvals/{approval_id}", dependencies=[Depends(admin)])
    def resolve(approval_id: str, request: ApprovalRequest) -> Any:
        return broker.resolve(approval_id, request.allow)

    @app.get("/openapi.json", dependencies=[Depends(admin)], include_in_schema=False)
    def schema() -> dict[str, Any]:
        return app.openapi()

    def operator_control() -> Control:
        if control is None:
            raise HTTPException(503, detail="Control plane unavailable in this embedding")
        return control

    @app.get("/events/page", dependencies=[Depends(admin)])
    def event_page(
        limit: int = Query(50, ge=1, le=100),
        before: int | None = Query(None, ge=1),
        status: str | None = Query(None, max_length=32),
        search: str = Query("", max_length=128),
        tool: str | None = Query(None, max_length=32),
        execution: str | None = Query(None, max_length=32),
    ) -> dict[str, Any]:
        return broker.audit.page(
            limit=limit, before=before, status=status, search=search, tool=tool, execution=execution
        )

    @app.put("/policy", dependencies=[Depends(admin)])
    def update_policy(request: PolicyUpdate) -> dict[str, str]:
        try:
            return {"digest": operator_control().update_policy(request)}
        except ValueError as exc:
            if str(exc) == "stale policy":
                raise HTTPException(
                    409, detail="Policy changed; reload before applying edits"
                ) from None
            raise HTTPException(422, detail="Invalid policy; no permissions changed") from None

    @app.get("/settings", dependencies=[Depends(admin)])
    def settings() -> dict[str, Any]:
        return {
            "settings": operator_control().settings.model_dump(),
            "raw_content_logging": False,
            "scope": "local synthetic workspace only",
            "available_modes": ["full"],
            "remote_access": False,
        }

    @app.put("/settings", dependencies=[Depends(admin)])
    def update_settings(request: Settings) -> dict[str, str]:
        operator_control().update_settings(request)
        return {"status": "saved"}

    @app.get("/integrations", dependencies=[Depends(admin)])
    def integrations() -> list[dict[str, Any]]:
        return operator_control().integrations()

    @app.get("/tasks", dependencies=[Depends(admin)])
    def tasks() -> list[dict[str, Any]]:
        from zyntrava.recovery import task_statuses

        return task_statuses(operator_control().state / "tasks.sqlite3")

    @app.get("/research/results", dependencies=[Depends(admin)])
    def results() -> list[dict[str, Any]]:
        return operator_control().results()

    @app.get("/research/results/{experiment_id}", dependencies=[Depends(admin)])
    def export(experiment_id: str) -> FileResponse:
        path = operator_control().result_path(experiment_id)
        return FileResponse(path, media_type="application/json", filename=path.name)

    @app.post("/research/jobs", dependencies=[Depends(admin)], status_code=202)
    def start_job(request: JobRequest) -> dict[str, Any]:
        try:
            return operator_control().start_job(request)
        except ValueError:
            raise HTTPException(
                409, detail="Job cannot start; check installation, capacity and active jobs"
            ) from None

    @app.get("/research/jobs", dependencies=[Depends(admin)])
    def jobs() -> list[dict[str, Any]]:
        service = operator_control()
        with service.lock:
            return [dict(job) for job in reversed(service.jobs.values())]

    if dashboard and dashboard.is_dir():
        app.mount("/app", StaticFiles(directory=dashboard, html=True), name="dashboard")

    return app
