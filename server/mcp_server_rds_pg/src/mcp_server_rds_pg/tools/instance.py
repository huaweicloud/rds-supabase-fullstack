# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Scenario tools: RDS for PostgreSQL instance lifecycle (P0-1)."""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_server_rds_pg.server import mcp
from mcp_server_rds_pg.service.instance_service import InstanceService


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_instances(
    name: str | None = None,
    instance_id: str | None = None,
    limit: int = 20,
    offset: int | None = None,
) -> dict[str, Any]:
    """List RDS for PostgreSQL instances in the current region.

    Scenario: inventory of instances - status, action locks, engine version,
    flavor, charge mode and connection addresses.

    Args:
        name: optional fuzzy instance-name filter.
        instance_id: fetch one exact instance id.
        limit: max instances to return, 1-100 (default 20).
        offset: page offset returned as marker by a previous call.

    Returns:
        Paginated envelope with instance summaries.
    """
    return await InstanceService().list_instances(
        name=name, instance_id=instance_id, limit=limit, offset=offset
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_instance(instance_id: str) -> dict[str, Any]:
    """Get one RDS for PostgreSQL instance detail.

    Scenario: check an instance's current state (status, current_actions,
    connection info) before issuing operations or after a job completes.

    Args:
        instance_id: exact instance id (from list_pg_instances).

    Returns:
        Instance detail envelope.
    """
    return await InstanceService().show_instance(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_instance_job(job_id: str) -> dict[str, Any]:
    """Show the status of an async RDS job (create/reboot/resize...).

    Scenario: a write tool returned a job_id; poll this until terminal state.
    Completed/Failed are terminal; anything else means still running.

    Args:
        job_id: job id returned by create/mutate results.

    Returns:
        Job detail: status, create/end time, fail_reason, entities.
    """
    return await InstanceService().show_job(job_id=job_id)


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def reboot_pg_instance(
    instance_id: str, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Reboot an RDS for PostgreSQL instance (two-stage).

    Stage 1: call with confirm=false to preview (returns plan_id).
    Stage 2: re-call with the same arguments plus confirm=true and plan_id.

    Args:
        instance_id: exact instance id.
        confirm: set true only after presenting the preview to the user.
        plan_id: the plan returned by the preview call.

    Returns:
        Preview envelope (changes, warnings, plan_id) or submission result
        with job_id and follow-up hints.
    """
    return await InstanceService().reboot(
        instance_id=instance_id, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def stop_pg_instance(
    instance_id: str, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Stop a pay-per-use RDS for PostgreSQL instance (two-stage).

    Only postPaid instances can be stopped; prePaid instances are rejected.
    Storage charges continue while stopped.

    Args:
        instance_id: exact instance id.
        confirm: set true only after presenting the preview to the user.
        plan_id: the plan returned by the preview call.

    Returns:
        Preview envelope or submission result with job_id.
    """
    return await InstanceService().stop(
        instance_id=instance_id, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def start_pg_instance(
    instance_id: str, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Start a stopped RDS for PostgreSQL instance (two-stage).

    Args:
        instance_id: exact instance id.
        confirm: set true only after presenting the preview to the user.
        plan_id: the plan returned by the preview call.

    Returns:
        Preview envelope or submission result with job_id.
    """
    return await InstanceService().start(
        instance_id=instance_id, confirm=confirm, plan_id=plan_id
    )
