# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the instance lifecycle service scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from huaweicloud_mcp_core.errors import McpToolError

from conftest import FakeSdkRdsClient
from mcp_huaweicloud_rds_pg.service.instance_service import InstanceService
from mcp_huaweicloud_rds_pg.service.plans import PlanStore


@pytest.fixture
def service(fake_client: FakeSdkRdsClient, plans: PlanStore) -> InstanceService:
    return InstanceService(client=fake_client, plans=plans)


async def test_list_instances(service: InstanceService) -> None:
    result = await service.list_instances(limit=20)
    assert result["count"] == 1
    item = result["items"][0]
    assert item["id"] == "inst-1"
    assert item["charge_mode"] == "postPaid"
    assert item["datastore"]["type"] == "PostgreSQL"


async def test_list_instances_filters_by_name(service: InstanceService) -> None:
    result = await service.list_instances(name="nope")
    assert result["items"] == []


async def test_show_instance(service: InstanceService) -> None:
    result = await service.show_instance(instance_id="inst-1")
    assert result["id"] == "inst-1"
    assert result["status"] == "ACTIVE"


async def test_show_instance_not_found(service: InstanceService) -> None:
    with pytest.raises(McpToolError) as excinfo:
        await service.show_instance(instance_id="inst-missing")
    assert excinfo.value.code == "MCP_NOT_FOUND"


async def test_show_job(service: InstanceService, fake_client: FakeSdkRdsClient) -> None:
    fake_client.jobs["job-1"] = {
        "id": "job-1",
        "name": "RestartDBInstance",
        "status": "Completed",
        "created": "2026-11-23",
    }
    result = await service.show_job(job_id="job-1")
    assert result["id"] == "job-1"
    assert result["status"] == "Completed"


async def test_show_job_not_found(service: InstanceService) -> None:
    with pytest.raises(McpToolError) as excinfo:
        await service.show_job(job_id="job-missing")
    assert excinfo.value.code == "MCP_NOT_FOUND"


async def test_reboot_two_stage(
    service: InstanceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    preview = await service.reboot(instance_id="inst-1", confirm=False, plan_id=None)
    assert preview["status"] == "confirmation_required"
    assert preview["warnings"]
    result = await service.reboot(
        instance_id="inst-1", confirm=True, plan_id=preview["plan_id"]
    )
    assert result["status"] == "submitted"


async def test_stop_rejects_prepaid(
    service: InstanceService, fake_client: FakeSdkRdsClient
) -> None:
    fake_client.instances["inst-1"]["charge_info"] = {"charge_mode": "prePaid"}
    with pytest.raises(McpToolError) as excinfo:
        await service.stop(instance_id="inst-1", confirm=False, plan_id=None)
    assert excinfo.value.code == "MCP_INVALID_ARGS"


async def test_stop_two_stage(
    service: InstanceService, fake_client: FakeSdkRdsClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    preview = await service.stop(instance_id="inst-1", confirm=False, plan_id=None)
    result = await service.stop(
        instance_id="inst-1", confirm=True, plan_id=preview["plan_id"]
    )
    assert result["status"] == "submitted"
    assert fake_client.instances["inst-1"]["status"] == "STOPPED"


async def test_start_skips_active_recheck(
    service: InstanceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Start legitimately targets non-ACTIVE (stopped) instances."""
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    fake_client = service._client  # type: ignore[assignment]
    fake_client.instances["inst-1"]["status"] = "STOPPED"
    fake_client.instances["inst-1"]["current_actions"] = []
    preview = await service.start(instance_id="inst-1", confirm=False, plan_id=None)
    result = await service.start(
        instance_id="inst-1", confirm=True, plan_id=preview["plan_id"]
    )
    assert result["status"] == "submitted"
    assert fake_client.instances["inst-1"]["status"] == "ACTIVE"


# --- defect-fix regression tests (R1-R8 verification, 2026-11-27) ------------


class _CapturingClient:
    """Bare client fake that records the exact SDK request objects built by
    the client layer (verifies kwarg/constructor bugs like R3's name vs
    user_name without touching the cloud)."""

    def __init__(self) -> None:
        self.captured: list[tuple[str, Any]] = []

    def update_postgresql_db_user_comment(self, request: Any) -> dict[str, Any]:
        self.captured.append(("update_user_comment", request))
        return {"result": "ok"}

    def update_port(self, request: Any) -> dict[str, Any]:
        self.captured.append(("update_port", request))
        return {"job_id": "job-port-1", "port": request.body.port}

    def create_alarm(self, request: Any) -> dict[str, Any]:
        self.captured.append(("create_alarm", request))
        return {"alarm_id": "al-1"}


@pytest.mark.asyncio
async def test_r3_user_comment_request_binds_user_name() -> None:
    """R3 regression: the request must be built with user_name= (the SDK
    model signature), not name= - previously raised TypeError at call time."""
    from mcp_huaweicloud_rds_pg.client.backup_db_apis import PgDatabaseMixin

    class _Api(PgDatabaseMixin):
        _client = _CapturingClient()

    api = _Api()
    result = await api.update_pg_db_user_comment(
        instance_id="inst-1", name="mcp_user", comment="regression"
    )
    request = api._client.captured[0][1]
    assert request.user_name == "mcp_user"
    assert request.body.comment == "regression"
    assert result == {"result": "ok"}


@pytest.mark.asyncio
async def test_r1_port_request_binds_int() -> None:
    """R1 regression: port must bind as int into UpdateDbPortRequest."""
    from mcp_huaweicloud_rds_pg.client.connection_apis import ConnectionMixin

    class _Api(ConnectionMixin):
        _client = _CapturingClient()

    api = _Api()
    await api.update_port(instance_id="inst-1", port=5433)
    request = api._client.captured[0][1]
    assert request.body.port == 5433
    assert isinstance(request.body.port, int)


@pytest.mark.asyncio
async def test_r6_alarm_condition_numeric_types() -> None:
    """R6 regression: CES Condition period/value must be int/float."""
    from mcp_huaweicloud_rds_pg.client.m3_apis import CesClient

    api = CesClient.__new__(CesClient)
    api._client = _CapturingClient()
    await api.create_alarm(
        name="r6", description=None, namespace="SYS.RDS",
        metric_name="rds001_cpu_util", dim_0="inst-1",
        comparison_operator=">=", value=85,
    )
    request = api._client.captured[0][1]
    cond = request.body.condition
    assert isinstance(cond.period, int) and cond.period == 300
    assert isinstance(cond.value, float) and cond.value == 85.0
