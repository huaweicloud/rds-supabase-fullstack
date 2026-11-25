# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Per-call guard helpers shared by every client mixin.

Agent-facing MCP consumers differ from humans in one decisive way: an LLM
will retry, poll and fan out without any human "thinking pause", so a single
slow or hanging cloud call blocks the agent's whole turn. Two protections
live here so every mixin gets them uniformly (see PERF-SPEC.md):

1. `guarded_call`  - wraps the synchronous SDK call with a hard timeout.
   Without it, asyncio.to_thread leaks an unbounded wait: the thread keeps
   running even after the MCP client gives up, and the agent stalls forever
   on the pending call. Timeouts keep the SDK's own (60/120s connect/read)
   but bound them at the orchestration level instead.
2. `throttle`      - client-side minimum interval between cloud calls.
   Agents polling in tight loops can trip IAM APIGW.0301 throttling (observed
   live: an overnight poll loop locked the whole account). The limiter is a
   simple async monotonic-interval gate: cheap, no bucket bookkeeping, and
   sufficient because the SDK channel is serial per process by design.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from typing import Any

from huaweicloud_mcp_core.errors import McpToolError

#: Default per-call timeout (seconds). Cloud read APIs answer well below 2s;
#: the 30s bound only exists so a wedged endpoint cannot pin the agent.
DEFAULT_CALL_TIMEOUT = 30.0

#: Minimum interval between cloud calls (seconds), IAM-protection default.
# Read once at import; RDS_PG_MIN_INTERVAL / RDS_PG_MIN_INTERVAL_SECONDS
# override it. 0 disables (tests and offline fakes).
_DEFAULT_INTERVAL_ENV = "RDS_PG_MIN_INTERVAL_SECONDS"

_last_call_monotonic = 0.0
_gate: asyncio.Lock | None = None


def _env_interval() -> float:
    raw = os.getenv(_DEFAULT_INTERVAL_ENV)
    if raw is None:
        return 0.2  # 5 rps ceiling: comfortably under IAM limits, invisible
        # for interactive agent pacing (a serial agent hop is >1s anyway).
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.2


async def throttle() -> None:
    """Enforce the minimum cloud-call interval for this process."""
    global _gate, _last_call_monotonic
    interval = _env_interval()
    if interval <= 0:
        return
    if _gate is None:
        _gate = asyncio.Lock()
    async with _gate:
        wait = _last_call_monotonic + interval - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_monotonic = time.monotonic()


_IAM_COOLDOWN_UNTIL: float = 0.0
_IAM_COOLDOWN_SECONDS = 300.0  # 401 APIGW.0301 -> whole-process cool-down 5 min


def _note_iam_auth_failure(message: str) -> None:
    """Circuit breaker: an IAM auth/lock error (APIGW.0301) trips a
    process-wide 5-minute cool-down. While tripped, guarded_call short-circuits
    with a clear envelope instead of hitting IAM again - the #1 lesson from the
    overnight lock incident: retrying while locked RENEWS the account lock."""
    global _IAM_COOLDOWN_UNTIL
    if "APIGW.0301" in message or "verify ak sk signature failed" in message:
        _IAM_COOLDOWN_UNTIL = max(_IAM_COOLDOWN_UNTIL, time.monotonic() + _IAM_COOLDOWN_SECONDS)


def _iam_cooldown_remaining() -> float:
    return max(0.0, _IAM_COOLDOWN_UNTIL - time.monotonic())


async def guarded_call(
    label: str,
    sync_call: Callable[[], dict[str, Any]],
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run one synchronous SDK call with throttle + timeout semantics.

    `label` names the operation for error envelopes. The wrapped call runs in
    a worker thread (same as asyncio.to_thread); on timeout we return
    immediately with a transport-class error - the thread may still complete
    in the background, which is exactly the "outcome unknown" case the mutate
    pipeline already classifies (see mutate.py: non-SDK exceptions -> unknown).
    """
    limit = timeout if timeout is not None else DEFAULT_CALL_TIMEOUT
    cooldown = _iam_cooldown_remaining()
    if cooldown > 0:
        raise McpToolError(
            "MCP_IAM_COOLDOWN",
            f"IAM authentication previously failed; process in cool-down for"
            f" another {cooldown:.0f}s to let the account-level lock expire",
            hint="Do NOT retry immediately - retries renew the IAM lock. Wait"
            " for the cool-down, then run one read-only probe"
            " (list_pg_instances) before resuming writes.",
        )
    await throttle()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(sync_call), timeout=limit
        )
        return result
    except McpToolError as exc:
        # IAM auth failures (APIGW.0301 / signature failed) trip the
        # process-wide cool-down so no further call renews the account lock.
        _note_iam_auth_failure(str(exc.message) if hasattr(exc, "message") else str(exc))
        raise
    except asyncio.TimeoutError:
        raise McpToolError(
            code="MCP_CALL_TIMEOUT",
            message=f"{label} timed out after {int(limit)}s",
            hint=(
                "The cloud call was abandoned, its outcome is unknown: do not"
                " retry write tools blind. For reads, retry after a short"
                " pause; for writes, reconcile state via show_pg_instance_job"
                " and the plan ledger before any resubmission."
            ),
        ) from None


def reset_throttle() -> None:
    """Test hook: clear the interval gate state."""
    global _gate, _last_call_monotonic
    _gate = None
    _last_call_monotonic = 0.0
