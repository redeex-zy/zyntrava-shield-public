"""Local durable, at-most-budget release reservations; no source values are stored.

The operator-owned audit database also holds this non-expiring ledger. Deleting,
rolling back or modifying state as the trusted OS owner is outside this boundary.
"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from zyntrava.paths import path_parts


class BudgetStateError(ValueError):
    """State requires operator review; never silently initialize over legacy releases."""


def initialize_release_state(conn: sqlite3.Connection) -> None:
    """Only AuditStore creating a new database may initialize this format."""
    conn.execute(
        "CREATE TABLE release_budget_meta_v1 (id INTEGER PRIMARY KEY CHECK(id=1), "
        "workspace TEXT, version INTEGER NOT NULL CHECK(version=1))"
    )
    conn.execute("INSERT INTO release_budget_meta_v1 VALUES(1,NULL,1)")
    conn.execute(
        "CREATE TABLE release_budgets_v1 (scope TEXT PRIMARY KEY, "
        "used INTEGER NOT NULL CHECK(typeof(used)='integer' AND used>=0))"
    )


class ReleaseBudgets:
    def __init__(self, database: Path, workspace: Path) -> None:
        self.database = database.resolve()
        # Same case-folded path semantics as the portable permission grammar.
        self.workspace = hashlib.sha256(
            workspace.resolve().as_posix().casefold().encode()
        ).hexdigest()

    def reserve(self, source: str, destination: str, limit: int) -> bool:
        """Commit one attempt BEFORE source access/audit/transport, including crashes.

        False means exhausted. Any exception means deny. No automatic renewal,
        refund, data-dependent identity or policy-digest-based reset is supported.
        """
        if not 1 <= limit <= 128:
            raise BudgetStateError("Invalid release budget.")
        scope = hashlib.sha256(
            json.dumps(
                [self.workspace, [p.casefold() for p in path_parts(source)], destination],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        # mode=rw prevents silently creating a missing state database. Lock waits bounded.
        with (
            closing(
                sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True, timeout=0.25)
            ) as conn,
            conn,
        ):
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('release_budget_meta_v1','release_budgets_v1')"
                )
            }
            if names != {"release_budget_meta_v1", "release_budgets_v1"}:
                # Purged audit history cannot establish that a legacy budget is unused.
                raise BudgetStateError(
                    "Legacy/incomplete release state requires operator migration."
                )
            metadata = conn.execute(
                "SELECT workspace,version FROM release_budget_meta_v1 WHERE id=1"
            ).fetchall()
            if metadata == [(None, 1)]:
                if conn.execute("SELECT count(*) FROM release_budgets_v1").fetchone()[0]:
                    raise BudgetStateError("Unbound ledger contains existing reservations.")
                conn.execute(
                    "UPDATE release_budget_meta_v1 SET workspace=? WHERE id=1", (self.workspace,)
                )
            elif metadata != [(self.workspace, 1)]:
                raise BudgetStateError("Release ledger identity mismatch; do not renew implicitly.")
            conn.execute("INSERT OR IGNORE INTO release_budgets_v1 VALUES(?,0)", (scope,))
            used = conn.execute(
                "SELECT used FROM release_budgets_v1 WHERE scope=?", (scope,)
            ).fetchone()[0]
            if type(used) is not int or used < 0:
                raise BudgetStateError("Invalid stored reservation count.")
            if used >= limit:
                return False
            conn.execute("UPDATE release_budgets_v1 SET used=used+1 WHERE scope=?", (scope,))
            return True
