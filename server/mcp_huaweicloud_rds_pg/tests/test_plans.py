# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the PlanStore ledger: issue/claim/finish plus all guard rails."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

# Windows/NTFS: stat() maps ACLs to constant 0o666 - POSIX bit
# assertions and symlink creation are Unix-only.
_windows = pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits / symlinks")
from huaweicloud_mcp_core.errors import McpToolError

from mcp_huaweicloud_rds_pg.service.plans import PlanStore, intent_digest


def digest(scope: dict) -> str:
    return intent_digest(scope)


SCOPE_A = {"service": "rds-pg", "instance_id": "inst-1", "operation": "reboot", "body": {}}
SCOPE_B = {"service": "rds-pg", "instance_id": "inst-2", "operation": "reboot", "body": {}}
SCOPE_A_MODIFIED = {
    "service": "rds-pg",
    "instance_id": "inst-1",
    "operation": "reboot",
    "body": {"extra": True},
}


async def test_issue_and_claim_happy_path(plans: PlanStore) -> None:
    issued = plans.issue(digest(SCOPE_A))
    assert issued["plan_id"] and issued["expires_at"] > time.time()
    plans.claim(issued["plan_id"], digest(SCOPE_A))  # no raise
    plans.finish(issued["plan_id"], "accepted", "job-1")
    record = plans.record(issued["plan_id"])
    assert record["state"] == "accepted"
    assert record["job_id"] == "job-1"


async def test_claim_rejects_unknown_plan(plans: PlanStore) -> None:
    with pytest.raises(McpToolError) as excinfo:
        plans.claim("no-such-plan", digest(SCOPE_A))
    assert excinfo.value.code == "MCP_GUARDRAIL_BLOCKED"


async def test_claim_rejects_digest_mismatch(plans: PlanStore) -> None:
    issued = plans.issue(digest(SCOPE_A))
    with pytest.raises(McpToolError):
        plans.claim(issued["plan_id"], digest(SCOPE_B))


async def test_claim_rejects_expired_plan(
    plans: PlanStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    issued = plans.issue(digest(SCOPE_A), ttl=1)
    real_time = time.time()
    monkeypatch.setattr(time, "time", lambda: real_time + 2)
    with pytest.raises(McpToolError):
        plans.claim(issued["plan_id"], digest(SCOPE_A))


async def test_claim_is_single_use(plans: PlanStore) -> None:
    issued = plans.issue(digest(SCOPE_A))
    plans.claim(issued["plan_id"], digest(SCOPE_A))
    with pytest.raises(McpToolError):
        plans.claim(issued["plan_id"], digest(SCOPE_A))  # state != prepared


async def test_claim_rejects_replay_of_unresolved_intent(plans: PlanStore) -> None:
    first = plans.issue(digest(SCOPE_A))
    plans.claim(first["plan_id"], digest(SCOPE_A))
    # The intent is in-flight (submitted); an identical re-preview must not
    # produce a usable second plan.
    second = plans.issue(digest(SCOPE_A))
    with pytest.raises(McpToolError) as excinfo:
        plans.claim(second["plan_id"], digest(SCOPE_A))
    assert "unresolved execution" in excinfo.value.message


async def test_claim_allows_retry_after_definite_failure(plans: PlanStore) -> None:
    first = plans.issue(digest(SCOPE_A))
    plans.claim(first["plan_id"], digest(SCOPE_A))
    plans.finish(first["plan_id"], "failed")
    second = plans.issue(digest(SCOPE_A))
    plans.claim(second["plan_id"], digest(SCOPE_A))  # no raise - safe to retry


async def test_digest_binds_instance_id(plans: PlanStore) -> None:
    """The grafting defense: a preview for inst-1 cannot submit inst-2."""
    issued = plans.issue(digest(SCOPE_A))
    with pytest.raises(McpToolError):
        plans.claim(issued["plan_id"], digest(SCOPE_B))


async def test_parameters_change_invalidates_plan(plans: PlanStore) -> None:
    issued = plans.issue(digest(SCOPE_A))
    with pytest.raises(McpToolError):
        plans.claim(issued["plan_id"], digest(SCOPE_A_MODIFIED))


async def test_inspect_never_leaks_digest(plans: PlanStore) -> None:
    issued = plans.issue(digest(SCOPE_A))
    result = plans.inspect(issued["plan_id"])
    assert "digest" not in result
    assert result["state"] == "prepared"


@_windows
async def test_state_file_permissions(plans: PlanStore, tmp_path: Path) -> None:
    plans.issue(digest(SCOPE_A))
    mode = os.stat(plans.path).st_mode & 0o777
    assert mode == 0o600
    parent_mode = os.stat(plans.path.parent).st_mode & 0o777
    assert parent_mode == 0o700


@_windows
async def test_symlink_state_file_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real.sqlite3"
    real.touch()
    link = tmp_path / "link.sqlite3"
    link.symlink_to(real)
    store = PlanStore(path=str(link))
    with pytest.raises(McpToolError):
        store.issue(digest(SCOPE_A))


async def test_env_override_for_state_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("RDS_PG_STATE_FILE", str(custom))
    store = PlanStore()
    store.issue(digest(SCOPE_A))
    assert custom.exists()


def test_intent_digest_is_deterministic_and_order_insensitive() -> None:
    left = intent_digest({"a": 1, "b": {"x": 2, "y": 3}})
    right = intent_digest({"b": {"y": 3, "x": 2}, "a": 1})
    assert left == right
    assert intent_digest({"a": 2}) != left
