"""Local append-only application audit. OS-level tamper resistance is not claimed."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class AuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, "
                "created_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def append(self, **fields: Any) -> str:
        event_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        payload = {"id": event_id, "created_at": now, **fields}
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO events(id,created_at,payload) VALUES(?,?,?)",
                (event_id, now, json.dumps(payload, ensure_ascii=True)),
            )
        return event_id

    def events(
        self, *, limit: int = 100, status: str | None = None, search: str = ""
    ) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM events WHERE "
                "(? IS NULL OR json_extract(payload,'$.status')=?) "
                "AND instr(lower(payload),lower(?))>0 ORDER BY seq DESC LIMIT ?",
                (status, status, search, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT json_extract(payload,'$.status'),count(*) FROM events "
                "WHERE json_extract(payload,'$.phase')='decision' "
                "GROUP BY json_extract(payload,'$.status')"
            ).fetchall()
            alerts = conn.execute(
                "SELECT count(*) FROM events WHERE json_extract(payload,'$.detected')=1"
            ).fetchone()
        counts = dict(rows)
        return {
            "evaluated_actions": sum(counts.values()),
            "blocked_actions": counts.get("blocked", 0),
            "allowed_actions": counts.get("allowed", 0),
            "approval_requests": counts.get("sent_for_approval", 0),
            "security_alert_events": int(alerts[0]),
        }

    def page(
        self,
        *,
        limit: int = 50,
        before: int | None = None,
        status: str | None = None,
        search: str = "",
        tool: str | None = None,
        execution: str | None = None,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT seq,payload FROM events WHERE (? IS NULL OR seq < ?) "
                "AND (? IS NULL OR json_extract(payload,'$.status')=?) "
                "AND (? IS NULL OR json_extract(payload,'$.tool')=?) "
                "AND (? IS NULL OR json_extract(payload,'$.execution')=?) "
                "AND instr(lower(payload),lower(?))>0 ORDER BY seq DESC LIMIT ?",
                (
                    before,
                    before,
                    status,
                    status,
                    tool,
                    tool,
                    execution,
                    execution,
                    search,
                    limit + 1,
                ),
            ).fetchall()
        return {
            "items": [{**json.loads(payload), "sequence": seq} for seq, payload in rows[:limit]],
            "next_cursor": rows[limit - 1][0] if len(rows) > limit else None,
        }

    def purge_before(self, cutoff: str) -> int:
        """Operator-only explicit retention control; never expose as an agent tool."""
        with self.connect() as conn:
            return conn.execute("DELETE FROM events WHERE created_at < ?", (cutoff,)).rowcount
