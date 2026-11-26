# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the RDS-PG tool layer: registration, guard declaration, invocation."""

from __future__ import annotations

from typing import Any

import pytest
from huaweicloud_mcp_core.security import ToolRisk, get_tool_risk, tool_supports_confirm

import mcp_huaweicloud_rds_pg.server  # noqa: F401  (import registers all tools)

EXPECTED_TOOLS = {
    "list_pg_instances": ToolRisk.READ,
    "show_pg_instance": ToolRisk.READ,
    "show_pg_instance_job": ToolRisk.READ,
    "reboot_pg_instance": ToolRisk.DANGEROUS,
    "stop_pg_instance": ToolRisk.DANGEROUS,
    "start_pg_instance": ToolRisk.DANGEROUS,
    "list_pg_flavors": ToolRisk.READ,
    "list_pg_datastores": ToolRisk.READ,
    "list_pg_storage_types": ToolRisk.READ,
    "show_pg_quotas": ToolRisk.READ,
    "plan_pg_instance_creation": ToolRisk.READ,
    "write_pg_secret_request": ToolRisk.WRITE,
    "create_pg_instance": ToolRisk.DANGEROUS,
    "reset_pg_admin_password": ToolRisk.WRITE,
    "show_pg_connection_info": ToolRisk.READ,
    "download_pg_ssl_cert": ToolRisk.READ,
    "change_pg_instance_port": ToolRisk.DANGEROUS,
    "change_pg_security_group": ToolRisk.DANGEROUS,
    "list_pg_hba_conf": ToolRisk.READ,
    "change_pg_hba_conf": ToolRisk.WRITE,
    "show_pg_dns_name": ToolRisk.READ,
    "create_pg_dns_name": ToolRisk.WRITE,
    "update_pg_dns_name": ToolRisk.WRITE,
    "show_pg_backup_policy": ToolRisk.READ,
    "set_pg_backup_policy": ToolRisk.WRITE,
    "create_pg_manual_backup": ToolRisk.WRITE,
    "list_pg_backups": ToolRisk.READ,
    "show_pg_backup_download_link": ToolRisk.READ,
    "list_pg_restore_times": ToolRisk.READ,
    "list_pg_databases": ToolRisk.READ,
    "create_pg_database": ToolRisk.WRITE,
    "list_pg_schemas": ToolRisk.READ,
    "create_pg_schema": ToolRisk.WRITE,
    "list_pg_db_users": ToolRisk.READ,
    "create_pg_db_user": ToolRisk.WRITE,
    "set_pg_db_user_password": ToolRisk.WRITE,
    "update_pg_db_user_comment": ToolRisk.WRITE,
    "grant_pg_db_privilege": ToolRisk.WRITE,
    "resize_pg_flavor": ToolRisk.DANGEROUS,
    "extend_pg_volume": ToolRisk.DANGEROUS,
    "reduce_pg_volume": ToolRisk.DANGEROUS,
    "set_pg_auto_enlarge_policy": ToolRisk.WRITE,
    "switch_pg_single_to_ha": ToolRisk.DANGEROUS,
    "change_pg_ops_window": ToolRisk.WRITE,
    "list_pg_read_replicas": ToolRisk.READ,
    "show_pg_metric_data": ToolRisk.READ,
    "create_pg_alarm_rule": ToolRisk.WRITE,
    "list_pg_resource_metrics": ToolRisk.READ,
    "list_pg_error_logs": ToolRisk.READ,
    "list_pg_slow_logs": ToolRisk.READ,
    "download_pg_error_log": ToolRisk.READ,
    "download_pg_slow_log": ToolRisk.READ,
    "set_pg_audit_log_policy": ToolRisk.WRITE,
    "list_pg_audit_logs": ToolRisk.READ,
    "show_pg_parameters": ToolRisk.READ,
    "update_pg_parameter": ToolRisk.WRITE,
    "list_pg_configurations": ToolRisk.READ,
    "apply_pg_configuration": ToolRisk.WRITE,
    "compare_pg_configurations": ToolRisk.READ,
    "list_pg_extensions": ToolRisk.READ,
    "install_pg_extension": ToolRisk.WRITE,
    "uninstall_pg_extension": ToolRisk.WRITE,
    "discover_pg_network": ToolRisk.READ,
    "list_pg_enterprise_projects": ToolRisk.READ,
    "list_pg_vpcs": ToolRisk.READ,
    "list_pg_subnets": ToolRisk.READ,
    "list_pg_security_groups": ToolRisk.READ,
    "create_pg_vpc": ToolRisk.WRITE,
    "create_pg_subnet": ToolRisk.WRITE,
    "create_pg_security_group": ToolRisk.WRITE,
    "create_pg_enterprise_project": ToolRisk.WRITE,
    "create_pg_eip": ToolRisk.WRITE,
    "bind_pg_instance_eip": ToolRisk.DANGEROUS,
    "unbind_pg_instance_eip": ToolRisk.DANGEROUS,
}


def test_all_tools_declare_risk() -> None:
    for tool_name, risk in EXPECTED_TOOLS.items():
        assert get_tool_risk(tool_name) is risk, tool_name


def test_mutation_tools_have_confirm_parameter() -> None:
    for tool_name in (
        "reboot_pg_instance",
        "stop_pg_instance",
        "start_pg_instance",
        "create_pg_instance",
        "reset_pg_admin_password",
        "create_pg_vpc",
        "create_pg_subnet",
        "create_pg_security_group",
        "create_pg_enterprise_project",
        "create_pg_eip",
        "bind_pg_instance_eip",
        "unbind_pg_instance_eip",
        "create_pg_dns_name",
        "update_pg_dns_name",
    ):
        assert tool_supports_confirm(tool_name) is True, tool_name
    assert tool_supports_confirm("list_pg_instances") is False
    assert tool_supports_confirm("discover_pg_network") is False


async def test_tools_are_registered_on_server() -> None:
    from mcp_huaweicloud_rds_pg.server import mcp

    tools = await mcp.list_tools()
    tool_names = {tool.name for tool in tools}
    assert tool_names == set(EXPECTED_TOOLS)


async def test_read_tool_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_pg_instances passes through the service with a fake client."""
    from mcp_huaweicloud_rds_pg.service.instance_service import InstanceService
    from mcp_huaweicloud_rds_pg.tools.instance import list_pg_instances

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

    import mcp_huaweicloud_rds_pg.tools.instance as instance_module

    original = instance_module.InstanceService
    instance_module.InstanceService = _FakeService  # type: ignore[misc]
    try:
        result = await list_pg_instances()
        assert result["items"][0]["id"] == "inst-1"
    finally:
        instance_module.InstanceService = original  # type: ignore[misc]
