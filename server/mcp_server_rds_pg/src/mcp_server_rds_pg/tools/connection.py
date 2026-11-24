# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 tools: connection management (P0-2).

EIP bind/unbind are deferred to the follow-up iteration (VPC/EIP channel).
"""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_server_rds_pg.server import mcp
from mcp_server_rds_pg.service.connection_service import ConnectionService


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_connection_info(instance_id: str) -> dict[str, Any]:
    """Get connection info for a PG instance: IPs, port, HA mode.

    Scenario: an application needs the psql/JDBC connection parameters.

    Args:
        instance_id: exact instance id.
    """
    return await ConnectionService().show_connection_info(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def download_pg_ssl_cert(instance_id: str) -> dict[str, Any]:
    """Get the temporary SSL certificate download link for an instance.

    Scenario: enabling sslmode=verify-ca connections.

    Args:
        instance_id: exact instance id.
    """
    return await ConnectionService().download_ssl_cert(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def change_pg_instance_port(
    instance_id: str, port: int, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Change the database port of an instance (two-stage, restarts DB).

    The change takes 4-10 minutes with connection downtime.

    Args:
        instance_id: exact instance id.
        port: new port (1-65535).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ConnectionService().change_port(
        instance_id=instance_id, port=port, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def change_pg_security_group(
    instance_id: str,
    security_group_id: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Replace the instance's security group (two-stage, full replacement).

    The given group replaces the current one entirely - its rules define all
    database access from this moment on.

    Args:
        instance_id: exact instance id.
        security_group_id: target security group id.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ConnectionService().change_security_group(
        instance_id=instance_id,
        security_group_id=security_group_id,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_hba_conf(instance_id: str) -> dict[str, Any]:
    """List pg_hba.conf client-authentication rules of an instance.

    Scenario: reviewing which hosts/users can authenticate before changes.
    """
    return await ConnectionService().list_hba_conf(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def change_pg_hba_conf(
    instance_id: str,
    entries: list[dict[str, Any]],
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Modify pg_hba.conf rules (two-stage; immediate for new connections).

    Args:
        instance_id: exact instance id.
        entries: rule list; each entry requires
            type/database/user/address/method (mask optional; priority
            0-10000, smaller = evaluated earlier).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ConnectionService().change_hba_conf(
        instance_id=instance_id, entries=entries, confirm=confirm, plan_id=plan_id
    )
