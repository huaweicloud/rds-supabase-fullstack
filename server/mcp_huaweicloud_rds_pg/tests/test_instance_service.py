# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the instance lifecycle service scenarios."""

from __future__ import annotations

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
