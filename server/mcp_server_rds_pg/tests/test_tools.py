# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the RDS-PG tool layer: registration, guard declaration, invocation."""

from __future__ import annotations

from typing import Any

import pytest
from huaweicloud_mcp_core.security import ToolRisk, get_tool_risk, tool_supports_confirm

import mcp_server_rds_pg.server  # noqa: F401  (import registers all tools)

EXPECTED_TOOLS = {
    "list_pg_instances": ToolRisk.READ,
    "show_pg_instance": ToolRisk.READ,
    "show_pg_instance_job": ToolRisk.READ,
    "reboot_pg_instance": ToolRisk.DANGEROUS,
    "stop_pg_instance": ToolRisk.DANGEROUS,
    "start_pg_instance": ToolRisk.DANGEROUS,
}


def test_all_tools_declare_risk() -> None:
    for tool_name, risk in EXPECTED_TOOLS.items():
        assert get_tool_risk(tool_name) is risk, tool_name


def test_mutation_tools_have_confirm_parameter() -> None:
    for tool_name in ("reboot_pg_instance", "stop_pg_instance", "start_pg_instance"):
        assert tool_supports_confirm(tool_name) is True, tool_name
    assert tool_supports_confirm("list_pg_instances") is False


async def test_tools_are_registered_on_server() -> None:
    from mcp_server_rds_pg.server import mcp

    tools = await mcp.list_tools()
    tool_names = {tool.name for tool in tools}
    assert tool_names == set(EXPECTED_TOOLS)


async def test_read_tool_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_pg_instances passes through the service with a fake client."""
    from mcp_server_rds_pg.service.instance_service import InstanceService
    from mcp_server_rds_pg.tools.instance import list_pg_instances

    class _FakeService(InstanceService):
        def __init__(self) -> None:
            pass

        async def list_instances(
            self,
            *,
            name: str | None = None,
            instance_id: str | None = None,
            limit: int = 20,
            offset: int | None = None,
        ) -> dict[str, Any]:
            return {"items": [{"id": "inst-1"}], "count": 1, "total": 1,
                    "marker": None, "truncated": False}

    import mcp_server_rds_pg.tools.instance as instance_module

    original = instance_module.InstanceService
    instance_module.InstanceService = _FakeService  # type: ignore[misc]
    try:
        result = await list_pg_instances()
        assert result["items"][0]["id"] == "inst-1"
    finally:
        instance_module.InstanceService = original  # type: ignore[misc]
