# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Local, durable, one-use intent ledger. Stores digests, not request bodies or tokens.

Ported from mcp_server_rds_supabase_mgr/service/plans.py with two RDS-specific
adjustments:

1. The intent digest MUST include the target instance_id so a preview issued
   for instance A can never be claimed for a submit against instance B
   (parameter-grafting defense).
2. The default state-file path is service-specific.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from huaweicloud_mcp_core.errors import McpToolError

PLAN_TTL_SECONDS = 600  # previews are valid for 10 minutes, single use


def intent_digest(scope: dict[str, Any]) -> str:
    """Stable digest of a write intent.

    The scope dict must include every parameter that identifies the operation:
    at minimum {"instance_id": ..., "method": ..., "operation": ..., "body": ...}.
    For instance-less operations (e.g. create) pass the request-file fingerprint
    under "body_ref" instead of a raw secret body.
    """
    return hashlib.sha256(
        json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class PlanStore:
    """SQLite-backed one-use plan ledger (0700 dir / 0600 file, symlink-rejected)."""

    def __init__(self, path: str | None = None) -> None:
        default_path = str(Path.home() / ".local/state/huaweicloud-rds-pg/plans.sqlite3")
        env_path: str | None = os.getenv("RDS_PG_STATE_FILE")
        resolved: str = path or env_path or default_path
        self.path = Path(resolved)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise McpToolError(
                "MCP_GUARDRAIL_BLOCKED", "State file must not be a symlink"
            )
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        if os.name != "nt":
            os.chmod(self.path, 0o600)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute(
            "CREATE TABLE IF NOT EXISTS plans"
            " (id TEXT PRIMARY KEY, digest TEXT, expires REAL, state TEXT, job TEXT)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS verification"
            " (plan TEXT PRIMARY KEY, checked_at REAL, kind TEXT)"
        )
        db.commit()
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def issue(self, digest: str, ttl: int = PLAN_TTL_SECONDS) -> dict[str, Any]:
        plan = secrets.token_urlsafe(24)
        expires = time.time() + ttl
        with self.connect() as db:
            db.execute(
                "INSERT INTO plans VALUES (?,?,?,?,NULL)", (plan, digest, expires, "prepared")
            )
        return {"plan_id": plan, "expires_at": expires}

    def claim(self, plan: str, digest: str) -> None:
        """Validate and consume a plan: exists, digest matches, unexpired, unused.

        Rejects when an equivalent intent already has an unresolved execution
        (submitted/accepted/unknown) - the anti-replay defense for async RDS jobs.
        """
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT digest,expires,state FROM plans WHERE id=?", (plan,)
            ).fetchone()
            if not row or row[0] != digest or row[1] < time.time() or row[2] != "prepared":
                raise McpToolError(
                    "MCP_GUARDRAIL_BLOCKED",
                    "Plan missing, changed, expired or already used",
                    hint="Preview again only after reconciling prior executions.",
                )
            if db.execute(
                "SELECT 1 FROM plans WHERE digest=?"
                " AND state IN ('submitted','accepted','unknown')",
                (digest,),
            ).fetchone():
                raise McpToolError(
                    "MCP_GUARDRAIL_BLOCKED",
                    "Equivalent intent has an unresolved execution",
                    hint=(
                        "Reconcile the recorded operation; do not replay or delete its ledger."
                    ),
                )
            db.execute("UPDATE plans SET state='submitted' WHERE id=?", (plan,))

    def finish(self, plan: str, state: str, job: str | None = None) -> None:
        if state not in ("accepted", "unknown", "failed"):
            raise ValueError("Invalid execution state")
        with self.connect() as db:
            db.execute(
                "UPDATE plans SET state=?,job=? WHERE id=? AND state='submitted'",
                (state, job, plan),
            )

    def record(self, plan: str) -> dict[str, Any]:
        """Internal only: never expose the binding digest as a tool response."""
        with self.connect() as db:
            row = db.execute(
                "SELECT expires,state,job,digest FROM plans WHERE id=?", (plan,)
            ).fetchone()
            evidence = db.execute(
                "SELECT checked_at FROM verification WHERE plan=?", (plan,)
            ).fetchone()
        if not row:
            raise McpToolError("MCP_NOT_FOUND", "Unknown plan")
        return {
            "plan_id": plan,
            "expires_at": row[0],
            "state": row[1],
            "job_id": row[2],
            "digest": row[3],
            "resource_checked_at": evidence[0] if evidence else None,
        }

    def inspect(self, plan: str) -> dict[str, Any]:
        result = self.record(plan)
        result.pop("digest")
        return {
            **result,
            "resource_verified": result["state"] == "verified",
            "business_verified": False,
            "completion_verified": False,
        }
