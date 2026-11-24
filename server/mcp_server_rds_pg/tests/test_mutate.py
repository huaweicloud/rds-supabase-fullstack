# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the two-stage mutation pipeline."""

from __future__ import annotations

from typing import Any

import pytest
from huaweicloud_mcp_core.errors import McpToolError

from conftest import FakeSdkRdsClient
from mcp_server_rds_pg.service.mutate import run_mutation
from mcp_server_rds_pg.service.plans import PlanStore

OPERATION = "reboot"


def _notices() -> dict[str, Any]:
    return {"warnings": ["interrupts connections"]}


async def _preview_then_submit(
    plans: PlanStore,
    client: FakeSdkRdsClient,
    *,
    execute=None,
    body: dict[str, Any] | None = None,
    instance_id: str = "inst-1",
) -> dict[str, Any]:
    preview = await run_mutation(
        tool_name="reboot_pg_instance",
        instance_id=instance_id,
        operation=OPERATION,
        body=body,
        notices=_notices(),
        recheck=True,
        execute=execute or (lambda: client.reboot_instance(instance_id=instance_id)),
        plans=plans,
        client=client,
        confirm=False,
    )
    assert preview["status"] == "confirmation_required"
    assert preview["execution"] == "not_executed"
    assert preview.get("plan_id")
    assert preview["warnings"] == ["interrupts connections"]
    return await run_mutation(
        tool_name="reboot_pg_instance",
        instance_id=instance_id,
        operation=OPERATION,
        body=body,
        notices=_notices(),
        recheck=True,
        execute=execute or (lambda: client.reboot_instance(instance_id=instance_id)),
        plans=plans,
        client=client,
        confirm=True,
        plan_id=preview["plan_id"],
    )


async def test_preview_has_no_side_effect(
    plans: PlanStore, fake_client: FakeSdkRdsClient
) -> None:
    preview = await run_mutation(
        tool_name="reboot_pg_instance",
        instance_id="inst-1",
        operation=OPERATION,
        body={"instance_id": "inst-1"},
        notices=_notices(),
        recheck=True,
        execute=lambda: fake_client.reboot_instance(instance_id="inst-1"),
        plans=plans,
        client=fake_client,
        confirm=False,
    )
    assert preview["status"] == "confirmation_required"
    # No mutation call was made during preview.
    assert all(call[0] != "reboot_instance" for call in fake_client.calls)


async def test_submit_requires_plan_id(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    with pytest.raises(McpToolError) as excinfo:
        await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id="inst-1",
            operation=OPERATION,
            body={"instance_id": "inst-1"},
            notices=_notices(),
            recheck=False,
            execute=lambda: fake_client.reboot_instance(instance_id="inst-1"),
            plans=plans,
            client=fake_client,
            confirm=True,
            plan_id=None,
        )
    assert excinfo.value.code == "MCP_INVALID_ARGS"


async def test_read_only_env_blocks_submit(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    monkeypatch.setenv("HUAWEICLOUD_MCP_READ_ONLY", "true")
    with pytest.raises(McpToolError) as excinfo:
        await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id="inst-1",
            operation=OPERATION,
            body={"instance_id": "inst-1"},
            notices=_notices(),
            recheck=False,
            execute=lambda: fake_client.reboot_instance(instance_id="inst-1"),
            plans=plans,
            client=fake_client,
            confirm=True,
            plan_id="whatever",
        )
    assert excinfo.value.code == "MCP_READ_ONLY"


async def test_writes_require_enable_writes_env(
    plans: PlanStore, fake_client: FakeSdkRdsClient
) -> None:
    # RDS_PG_ENABLE_WRITES unset -> blocked even without read-only mode.
    with pytest.raises(McpToolError) as excinfo:
        await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id="inst-1",
            operation=OPERATION,
            body={"instance_id": "inst-1"},
            notices=_notices(),
            recheck=False,
            execute=lambda: fake_client.reboot_instance(instance_id="inst-1"),
            plans=plans,
            client=fake_client,
            confirm=True,
            plan_id="whatever",
        )
    assert excinfo.value.code == "MCP_READ_ONLY"


async def test_happy_path_submit(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    result = await _preview_then_submit(plans, fake_client)
    assert result["status"] == "submitted"
    assert result["result"]["job_id"] == "job-reboot-1"
    assert result["job_follow_up"]
    # Pre-submit recheck ran (a list_instances call precedes reboot_instance).
    kinds = [call[0] for call in fake_client.calls]
    assert "reboot_instance" in kinds
    assert kinds.index("list_instances") < kinds.index("reboot_instance")


async def test_action_lock_fails_closed(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    fake_client.instances["inst-1"]["current_actions"] = [{"action": "REBOOTING"}]
    with pytest.raises(McpToolError) as excinfo:
        await _preview_then_submit(plans, fake_client)
    assert excinfo.value.code == "MCP_GUARDRAIL_BLOCKED"
    # And no mutation call was made.
    assert all(call[0] != "reboot_instance" for call in fake_client.calls)


async def test_non_active_status_fails_closed(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    # REBOOTING is a real in-flight state that must never accept mutations.
    fake_client.instances["inst-1"]["status"] = "REBOOTING"
    with pytest.raises(McpToolError):
        await _preview_then_submit(plans, fake_client)


async def test_missing_instance_fails_closed(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    with pytest.raises(McpToolError) as excinfo:
        await _preview_then_submit(plans, fake_client, instance_id="inst-nope")
    assert excinfo.value.code == "MCP_GUARDRAIL_BLOCKED"


async def test_definite_rejection_marks_failed(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")

    async def _reject() -> dict[str, Any]:
        raise McpToolError("DBS.200001", "instance in use")

    preview = await run_mutation(
        tool_name="reboot_pg_instance",
        instance_id="inst-1",
        operation=OPERATION,
        body={"instance_id": "inst-1"},
        notices=_notices(),
        recheck=False,
        execute=_reject,
        plans=plans,
        client=fake_client,
        confirm=False,
    )
    with pytest.raises(McpToolError):
        await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id="inst-1",
            operation=OPERATION,
            body={"instance_id": "inst-1"},
            notices=_notices(),
            recheck=False,
            execute=_reject,
            plans=plans,
            client=fake_client,
            confirm=True,
            plan_id=preview["plan_id"],
        )
    record = plans.record(preview["plan_id"])
    assert record["state"] == "failed"
    # Retrying with the same args after a definite failure is allowed
    # (new preview + claim path works - see test_plans retry case).


async def test_unknown_outcome_marks_unknown_and_forbids_replay(
    plans: PlanStore, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")

    async def _timeout() -> dict[str, Any]:
        raise TimeoutError("transport timeout")

    preview = await run_mutation(
        tool_name="reboot_pg_instance",
        instance_id="inst-1",
        operation=OPERATION,
        body={"instance_id": "inst-1"},
        notices=_notices(),
        recheck=False,
        execute=_timeout,
        plans=plans,
        client=fake_client,
        confirm=False,
    )
    with pytest.raises(McpToolError) as excinfo:
        await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id="inst-1",
            operation=OPERATION,
            body={"instance_id": "inst-1"},
            notices=_notices(),
            recheck=False,
            execute=_timeout,
            plans=plans,
            client=fake_client,
            confirm=True,
            plan_id=preview["plan_id"],
        )
    assert excinfo.value.code == "MCP_SDK_ERROR"
    assert "do NOT resubmit" in (excinfo.value.hint or "")
    assert plans.record(preview["plan_id"])["state"] == "unknown"

    # Re-previewing the identical intent is blocked while unresolved.
    second = plans.issue(preview["plan_id"] and plans.record(preview["plan_id"])["digest"])
    # digest from record; claim must fail
    with pytest.raises(McpToolError):
        plans.claim(second["plan_id"], plans.record(preview["plan_id"])["digest"])


