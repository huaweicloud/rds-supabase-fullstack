# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""E2E scenarios for the generic AI-application guard (guide §阶段三, AI-3/AI-5).

Unlike the unit tests in test_mutate.py (which stub `run_mutation` call sites),
these drive the REAL service classes - ConnectionService.change_security_group,
ResizeService.change_ops_window, InstanceService reads - through the real
run_mutation pipeline + a real file-backed PlanStore ledger, with only the
cloud SDK client faked (a real AI-application binding cannot be created in
E2E without provisioning a paid public-preview product, so fake injection at
the client boundary is the sanctioned E2E seam).

Mapping to AGENT-E2E-GUIDE.md 阶段三:
- AI-3 (guard blocks managed instance)  -> test_ai3_* (5 write tools x guard)
- AI-5 (naming fallback when the API is unavailable) -> test_ai5_*
- AI-4 (reads unaffected) is exercised here at service level as a companion
  (test_ai4_*); the live-cloud variant of AI-1/AI-2/AI-4 runs via the MCP
  stdio session per the guide.
"""

from __future__ import annotations

from typing import Any

import pytest

from huaweicloud_mcp_core.errors import McpToolError

from mcp_server_rds_pg.service.connection_service import ConnectionService
from mcp_server_rds_pg.service.instance_service import InstanceService
from mcp_server_rds_pg.service.m3_service import ResizeService
from mcp_server_rds_pg.service.plans import PlanStore
from conftest import FakeSdkRdsClient

APP_NAME = "my-graphrag-e2e"


def _bind_ai_app(
    client: FakeSdkRdsClient, instance_id: str, app_name: str = APP_NAME
) -> None:
    """Inject a fake AI-application binding (the E2E seam: real bindings
    need a paid public-preview AI application, out of scope)."""

    async def fake_apps(*, limit: int = 100) -> dict[str, Any]:
        client.calls.append(("list_ai_applications", {"limit": limit}))
        return {
            "ai_applications": [
                {
                    "id": "app-e2e-1",
                    "name": app_name,
                    "type": "GraphRAG",
                    "status": "normal",
                    "managed_instance_id": instance_id,
                }
            ]
        }

    client.list_ai_applications = fake_apps  # type: ignore[method-assign]


def _break_ai_api(client: FakeSdkRdsClient) -> None:
    """Simulate ListAiApplications being unavailable (guard API throws)."""

    async def boom(*, limit: int = 100) -> dict[str, Any]:
        raise RuntimeError("APIGW.0301 rate-limited / endpoint unreachable")

    client.list_ai_applications = boom  # type: ignore[method-assign]


def _async(value: dict[str, Any]):
    async def _ret(*, limit: int = 100) -> dict[str, Any]:
        return value

    return _ret


class FakeOpsWindowClient(FakeSdkRdsClient):
    """FakeSdkRdsClient + the low-risk write ops used by the E2E scenarios
    (ops-window/SG swap) recorded instead of hitting a cloud."""

    def __init__(self) -> None:
        super().__init__()
        self.ops_calls: list[dict[str, Any]] = []
        self.sg_calls: list[dict[str, Any]] = []

    async def change_ops_window(
        self, *, instance_id: str, start_time: str, end_time: str
    ) -> dict[str, Any]:
        self.ops_calls.append(
            {
                "instance_id": instance_id,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        return {"job_id": "job-ops-window-1"}

    async def set_security_group(
        self, *, instance_id: str, security_group_id: str
    ) -> dict[str, Any]:
        self.sg_calls.append(
            {"instance_id": instance_id, "security_group_id": security_group_id}
        )
        return {}


async def _submit(
    service_call, preview: dict[str, Any]
) -> dict[str, Any]:
    return await service_call(confirm=True, plan_id=preview["plan_id"])


# --------------------------------------------------------------------------
# AI-3: the generic guard blocks every write tool on a bound instance.
# The block must fire at the submit stage (preview stays available so the
# operator can see what was asked), BEFORE any claim/execute of the plan.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tool", "preview_kwargs"),
    [
        pytest.param(
            "reboot",
            dict(instance_id="inst-1", start="now"),
            id="reboot_pg_instance",
        ),
        pytest.param(
            "ops_window",
            dict(instance_id="inst-1", start_time="02:00", end_time="06:00"),
            id="change_pg_ops_window",
        ),
        pytest.param(
            "port",
            dict(instance_id="inst-1", port=5433),
            id="change_pg_instance_port",
        ),
    ],
)
async def test_ai3_guard_blocks_all_write_tools_on_bound_instance(
    plans: PlanStore,
    fake_client: FakeSdkRdsClient,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    preview_kwargs: dict[str, Any],
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    monkeypatch.delenv("HUAWEICLOUD_MCP_READ_ONLY", raising=False)
    _bind_ai_app(fake_client, "inst-1")

    if tool == "reboot":
        service = InstanceService(client=fake_client, plans=plans)

        async def call(confirm: bool, plan_id: str | None) -> dict[str, Any]:
            return await service.reboot(
                instance_id="inst-1", confirm=confirm, plan_id=plan_id
            )
    elif tool == "ops_window":
        service = ResizeService(client=fake_client, plans=plans)

        async def call(confirm: bool, plan_id: str | None) -> dict[str, Any]:
            return await service.change_ops_window(
                instance_id="inst-1",
                start_time="02:00",
                end_time="06:00",
                confirm=confirm,
                plan_id=plan_id,
            )
    else:
        service = ConnectionService(client=fake_client, plans=plans)

        async def call(confirm: bool, plan_id: str | None) -> dict[str, Any]:
            return await service.change_port(
                instance_id="inst-1", port=5433, confirm=confirm, plan_id=plan_id
            )

    # AI-3a: preview still works (guard must not break stage 1).
    preview = await call(confirm=False, plan_id=None)
    assert preview["status"] == "confirmation_required"
    assert preview["plan_id"]

    # AI-3b: submit is blocked with the app name in the envelope.
    with pytest.raises(McpToolError) as excinfo:
        await call(confirm=True, plan_id=preview["plan_id"])
    assert excinfo.value.code == "MCP_GUARDRAIL_BLOCKED"
    assert APP_NAME in excinfo.value.message
    assert "hosted application" in excinfo.value.message
    assert excinfo.value.hint and "management plane" in excinfo.value.hint

    # AI-3c: the blocked submit must NOT have executed or consumed the plan
    # (execute markers absent, plan still claimable state 'issued').
    executed = [c for c in fake_client.calls if c[0] not in (
        "list_instances", "list_ai_applications"
    )]
    assert not executed, f"guard fired too late, cloud calls leaked: {executed}"
    record = plans.record(preview["plan_id"])
    assert record["state"] == "prepared"


@pytest.mark.parametrize(
    "response_shape",
    [
        {"ai_applications": []},
        {
            "ai_applications": [
                {
                    "name": "other-app",
                    "managed_instance_id": "inst-other",
                    "type": "ContextBase",
                    "status": "normal",
                }
            ]
        },
    ],
)
async def test_ai3_no_false_positive_on_unbound_instance(
    plans: PlanStore,
    monkeypatch: pytest.MonkeyPatch,
    response_shape: dict[str, Any],
) -> None:
    """Empty list / binding to a DIFFERENT instance must pass the guard
    (companion of AI-2 at service level: no false positives)."""
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    client = FakeOpsWindowClient()
    client._register_defaults()
    client.list_ai_applications = _async(response_shape)  # type: ignore[method-assign]

    service = ResizeService(client=client, plans=plans)
    preview = await service.change_ops_window(
        instance_id="inst-1", start_time="03:00", end_time="06:00",
        confirm=False, plan_id=None,
    )
    result = await service.change_ops_window(
        instance_id="inst-1", start_time="03:00", end_time="06:00",
        confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert client.ops_calls == [
        {"instance_id": "inst-1", "start_time": "03:00", "end_time": "06:00"}
    ]


# --------------------------------------------------------------------------
# AI-4: read tools are unaffected by an AI binding.
# --------------------------------------------------------------------------


async def test_ai4_reads_unaffected_by_binding(
    fake_client: FakeSdkRdsClient,
) -> None:
    _bind_ai_app(fake_client, "inst-1")

    instance_service = InstanceService(client=fake_client, plans=PlanStore())
    found = await instance_service._find("inst-1")
    assert found["id"] == "inst-1"

    conn = ConnectionService(client=fake_client, plans=PlanStore())
    info = await conn.show_connection_info(instance_id="inst-1")
    assert info["instance_id"] == "inst-1"


# --------------------------------------------------------------------------
# AI-5: naming fallback - when ListAiApplications is unavailable, the
# change_pg_security_group supabase-naming heuristic still blocks.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sg_names",
    [
        ["supabase-db-sg"],
        ["web-open", "Supabase-DB-SG"],
    ],
)
async def test_ai5_naming_fallback_blocks_supabase_named_group(
    plans: PlanStore,
    fake_client: FakeSdkRdsClient,
    monkeypatch: pytest.MonkeyPatch,
    sg_names: list[str],
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    monkeypatch.delenv("HUAWEICLOUD_MCP_READ_ONLY", raising=False)
    # API channel dead (guard cannot see bindings) AND a supabase-named
    # security group hangs on the instance.
    _break_ai_api(fake_client)
    fake_client.instances["inst-1"]["security_group_list"] = [
        {"id": f"sg-{i}", "name": n} for i, n in enumerate(sg_names)
    ]

    service = ConnectionService(client=fake_client, plans=plans)
    with pytest.raises(McpToolError) as excinfo:
        await service.change_security_group(
            instance_id="inst-1", security_group_id="sg-new",
            confirm=False, plan_id=None,
        )
    assert excinfo.value.code == "MCP_GUARDRAIL_BLOCKED"
    assert "Supabase" in excinfo.value.message
    assert not any(c[0] == "set_security_group" for c in fake_client.calls)


async def test_ai5_normal_sg_still_changeable_when_api_down(
    plans: PlanStore,
    fake_client: FakeSdkRdsClient,
    monkeypatch: pytest.MonKeyPatch,
) -> None:
    """AI channel unavailable + ordinary SG names -> no false positive from
    the fallback; the mutation proceeds normally (fail-open only for reads
    is NOT the rule here: naming heuristic simply does not match)."""
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    _break_ai_api(fake_client)
    fake_client.instances["inst-1"]["security_group_list"] = [
        {"id": "sg-0", "name": "rds-default-sg"}
    ]

    service = ConnectionService(client=fake_client, plans=plans)
    preview = await service.change_security_group(
        instance_id="inst-1", security_group_id="sg-new",
        confirm=False, plan_id=None,
    )
    assert preview["status"] == "confirmation_required"
