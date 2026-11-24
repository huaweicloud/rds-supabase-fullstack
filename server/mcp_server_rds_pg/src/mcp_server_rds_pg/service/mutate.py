# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Two-stage mutation pipeline for RDS-PG write tools.

Covers the three holes the core middleware's `confirm` flag cannot:
1. Parameter grafting  - preview instance A, submit instance B.
2. Timeout replay      - RDS jobs are async; a timed-out submit may already have
                         been applied, so blind retries double-charge.
3. TOCTOU              - the target's state may change between preview and submit.

Pipeline (mirrors mcp_server_rds_supabase_mgr/service/operations.py mutate):

    validate -> notices -> digest
      confirm=false -> preview envelope {changes, warnings, plan_id, expires_at}
      confirm=true  -> env gates -> claim(plan_id, digest)
                     -> pre-submit recheck (_assert_mutation_ready)
                     -> execute (SDK call)
                     -> classify: definite rejection -> failed (safe to retry
                        with new args); unknown outcome -> unknown (NEVER replay)
                     -> finish(accepted, job_id)
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.guardrails import assert_not_protected

from mcp_server_rds_pg.client.sdk_rds import SdkRdsClient
from mcp_server_rds_pg.service.plans import PlanStore, intent_digest

_JOB_FOLLOW_UP = (
    "Accepted (202/job_id) is not done: poll show_pg_instance_job until the job "
    "reports Completed, then re-check the instance (status ACTIVE and no "
    "current_actions) before issuing further operations."
)

_MUTATION_READY_STATES = {"ACTIVE"}


def _writes_disabled() -> bool:
    return os.getenv("RDS_PG_ENABLE_WRITES") != "true" or os.getenv(
        "HUAWEICLOUD_MCP_READ_ONLY", "false"
    ).lower() == "true"


async def _assert_mutation_ready(
    client: SdkRdsClient, instance_id: str, tool_name: str
) -> None:
    """Pre-submit recheck: the real target must be demonstrably ready.

    Unknown/missing instances and action-locked instances fail closed - a task
    submitted against an instance mid-restart/resize conflicts or corrupts state.
    """
    response = await client.list_instances(limit=1, marker=None, id=instance_id)
    instances = response.get("instances") or []
    target = instances[0] if instances else None
    if not target or target.get("id") != instance_id:
        raise McpToolError(
            "MCP_GUARDRAIL_BLOCKED",
            f"Instance {instance_id} not found for mutation",
            hint="List instances first (list_pg_instances) and retry with the exact id.",
        )
    status = str(target.get("status") or "").upper()
    if status not in _MUTATION_READY_STATES or target.get("current_actions"):
        raise McpToolError(
            "MCP_GUARDRAIL_BLOCKED",
            "Target is not demonstrably ready for mutation",
            hint=(
                f"Instance status is {status or 'unknown'}"
                + (" with actions in flight" if target.get("current_actions") else "")
                + "; wait for the running operation to finish (show_pg_instance_job)"
                " and retry."
            ),
        )
    # Second defense line: resource-level protection by real cloud attributes.
    assert_not_protected(
        {
            "id": target.get("id"),
            "name": target.get("name"),
            "tags": target.get("tags"),
        },
        tool_name=tool_name,
    )


async def run_mutation(
    *,
    tool_name: str,
    instance_id: str | None,
    operation: str,
    body: dict[str, Any] | None,
    notices: dict[str, Any],
    recheck: bool,
    execute: Callable[[], Awaitable[dict[str, Any]]],
    plans: PlanStore,
    client: SdkRdsClient,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Generic two-stage pipeline shared by every write tool.

    Args:
        tool_name:    calling tool name (auditing + protection rules).
        instance_id:  target instance (None only for instance-creating operations
                      whose digest then binds to the operation + body).
        operation:    logical operation label for the digest (e.g. "reboot").
        body:         mutation arguments. Secret values must already be replaced
                      by request-file references (request_ref) by the caller.
        notices:      scenario warnings embedded in both preview and result.
        recheck:      when True, run the pre-submit instance recheck (lifecycle
                      and config mutations). Instance-creating tools pass False.
        execute:      the actual SDK call; must raise McpToolError on definite
                      rejection and let other exceptions bubble (classified
                      as unknown).
        plans:        PlanStore instance (injected for tests).
        client:       SDK client (injected for tests).
        confirm:      stage-2 flag.
        plan_id:      plan returned by the preview call.
    """
    scope = {
        "service": "rds-pg",
        "instance_id": instance_id,
        "operation": operation,
        "body": body or {},
    }
    digest = intent_digest(scope)
    if not confirm:
        preview = {k: v for k, v in (body or {}).items()}
        return {
            "status": "confirmation_required",
            **({"instance_id": instance_id} if instance_id else {}),
            "action": operation,
            "changes": preview,
            "execution": "not_executed",
            **notices,
            **plans.issue(digest),
        }

    if _writes_disabled():
        raise McpToolError(
            "MCP_READ_ONLY",
            "Writes are disabled",
            hint="Set RDS_PG_ENABLE_WRITES=true and HUAWEICLOUD_MCP_READ_ONLY unset, "
            "then restart the server.",
        )
    if not plan_id:
        raise McpToolError(
            "MCP_INVALID_ARGS",
            "confirm=true requires the plan_id returned by the preview call",
            hint="Call this tool with confirm=false first, present the changes, then "
            "resubmit with confirm=true and the returned plan_id.",
        )
    plans.claim(plan_id, digest)
    if recheck and instance_id:
        await _assert_mutation_ready(client, instance_id, tool_name)
    try:
        result = await execute()
    except McpToolError:
        plans.finish(plan_id, "failed")
        raise
    except BaseException:
        plans.finish(plan_id, "unknown")
        raise McpToolError(
            "MCP_SDK_ERROR",
            "Write result unknown",
            hint=_UNKNOWN_HINT,
            request_id=None,
        ) from None
    plans.finish(plan_id, "accepted", _extract_job_id(result))
    return {"status": "submitted", "result": result, "plan_id": plan_id,
            "job_follow_up": _JOB_FOLLOW_UP, **notices}


_UNKNOWN_HINT = (
    "Submission outcome unknown (timeout or transport error). The operation may "
    "already be applied. Query show_pg_instance_job and the target instance state; "
    "do NOT resubmit - previews and the recorded intent are single-use."
)


def _extract_job_id(result: dict[str, Any]) -> str | None:
    for key in ("job_id", "jobId", "task_id", "taskId"):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    nested = result.get("job")
    if isinstance(nested, dict):
        return _extract_job_id(nested)
    return None
