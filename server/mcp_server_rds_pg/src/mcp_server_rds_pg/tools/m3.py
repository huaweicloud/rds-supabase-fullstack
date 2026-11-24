# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M3 tools: resize/replicas, monitoring, logs, parameters, extensions (P1)."""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_server_rds_pg.server import mcp
from mcp_server_rds_pg.service.m3_service import (
    ExtensionService,
    LogService,
    MonitorService,
    ParamService,
    ResizeService,
)

# --- P1-5 resize -------------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def resize_pg_flavor(
    instance_id: str, spec_code: str, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Change an instance's CPU/memory flavor (two-stage; restarts the DB).

    Args:
        instance_id: exact instance id.
        spec_code: target flavor spec code (from list_pg_flavors).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().resize_flavor(
        instance_id=instance_id, spec_code=spec_code, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def extend_pg_volume(
    instance_id: str, size: int, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Enlarge an instance's disk (two-stage; no downtime, billing grows).

    Args:
        instance_id: exact instance id.
        size: new total size GB (must be larger than current).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().extend_volume(
        instance_id=instance_id, size=size, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def reduce_pg_volume(
    instance_id: str, size: int, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Reduce an instance's disk (two-stage; engine 17+ only).

    Args:
        instance_id: exact instance id.
        size: new total size GB (must be smaller than current).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().reduce_volume(
        instance_id=instance_id, size=size, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def set_pg_auto_enlarge_policy(
    instance_id: str,
    switch_option: bool,
    limit_size: int | None = None,
    trigger_threshold: int | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Set the auto disk-enlarge policy (two-stage).

    Args:
        instance_id: exact instance id.
        switch_option: enable/disable the policy.
        limit_size: max size GB.
        trigger_threshold: remaining-space percent trigger.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().set_auto_enlarge_policy(
        instance_id=instance_id,
        switch_option=switch_option,
        limit_size=limit_size,
        trigger_threshold=trigger_threshold,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def switch_pg_single_to_ha(
    instance_id: str,
    az_code_new_node: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Convert a Single instance to Ha (two-stage; restart + ~2x billing).

    Args:
        instance_id: exact instance id (Single mode).
        az_code_new_node: AZ for the new standby node.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().switch_single_to_ha(
        instance_id=instance_id,
        az_code_new_node=az_code_new_node,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def change_pg_ops_window(
    instance_id: str,
    start_time: str,
    end_time: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Set the maintenance window (two-stage).

    Args:
        instance_id: exact instance id.
        start_time: window start, e.g. "02:00".
        end_time: window end, e.g. "06:00" (max 4h window, no cross-midnight).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ResizeService().change_ops_window(
        instance_id=instance_id,
        start_time=start_time,
        end_time=end_time,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_read_replicas(primary_id: str) -> dict[str, Any]:
    """List read replicas attached to a primary instance.

    Args:
        primary_id: the primary instance id.
    """
    return await ResizeService().list_read_replicas(primary_id=primary_id)


# --- P1-7 monitoring ----------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_metric_data(
    instance_id: str,
    metric_name: str,
    period: int = 300,
    time_range: int = 3600,
) -> dict[str, Any]:
    """Read metric datapoints for an instance (CES channel).

    Args:
        instance_id: exact instance id.
        metric_name: e.g. rds001_cpu_util, rds061_disk_used (see
            list_pg_resource_metrics for the full set).
        period: sampling period seconds (300 default).
        time_range: lookback seconds from now (3600 = last hour).
    """
    return await MonitorService().show_metric_data(
        instance_id=instance_id,
        metric_name=metric_name,
        period=period,
        time_range=time_range,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_alarm_rule(
    instance_id: str,
    name: str,
    metric_name: str,
    comparison_operator: str = ">=",
    value: float = 85,
    description: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Create a CES alarm rule for an instance metric (middleware confirm).

    Args:
        instance_id: exact instance id.
        name: alarm rule name.
        metric_name: metric to watch (e.g. rds001_cpu_util).
        comparison_operator: e.g. ">=".
        value: threshold value.
        description: optional text.
        confirm: middleware confirm flag.
    """
    return await MonitorService().create_alarm_rule(
        name=name,
        description=description,
        metric_name=metric_name,
        instance_id=instance_id,
        comparison_operator=comparison_operator,
        value=value,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_resource_metrics() -> dict[str, Any]:
    """List RDS-for-PostgreSQL monitoring metrics and their dimensions."""
    return await MonitorService().list_resource_metrics()


# --- P1-8 logs -----------------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_error_logs(
    instance_id: str, start_date: str, end_date: str, limit: int = 20
) -> dict[str, Any]:
    """List error log events in a time range.

    Args:
        instance_id: exact instance id.
        start_date/end_date: "YYYY-MM-DDTHH:MM:SSZ" (UTC).
        limit: page size 1-100.
    """
    return await LogService().list_error_logs(
        instance_id=instance_id, start_date=start_date, end_date=end_date, limit=limit
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_slow_logs(
    instance_id: str, start_date: str, end_date: str, limit: int = 20
) -> dict[str, Any]:
    """List slow SQL events in a time range.

    Args:
        instance_id: exact instance id.
        start_date/end_date: "YYYY-MM-DDTHH:MM:SSZ" (UTC).
        limit: page size 1-100.
    """
    return await LogService().list_slow_logs(
        instance_id=instance_id, start_date=start_date, end_date=end_date, limit=limit
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def download_pg_error_log(instance_id: str) -> dict[str, Any]:
    """Get error-log download links (temporary URLs)."""
    return await LogService().download_error_log(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def download_pg_slow_log(instance_id: str) -> dict[str, Any]:
    """Get slow-log download links (temporary URLs)."""
    return await LogService().download_slow_log(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def set_pg_audit_log_policy(
    instance_id: str, keep_days: int, confirm: bool = False, plan_id: str | None = None
) -> dict[str, Any]:
    """Enable/set SQL audit retention (two-stage; billing by volume).

    Args:
        instance_id: exact instance id.
        keep_days: retention days (0 disables audit).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await LogService().set_auditlog_policy(
        instance_id=instance_id, keep_days=keep_days, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_audit_logs(instance_id: str, limit: int = 20) -> dict[str, Any]:
    """List SQL audit events (requires audit policy enabled)."""
    return await LogService().list_audit_logs(instance_id=instance_id, limit=limit)


# --- P1-9 parameters -----------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_parameters(
    instance_id: str, name: str | None = None
) -> dict[str, Any]:
    """Show instance database parameters (optionally one by name).

    Args:
        instance_id: exact instance id.
        name: optional exact parameter name (e.g. max_connections).
    """
    return await ParamService().show_parameters(instance_id=instance_id, name=name)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def update_pg_parameter(
    instance_id: str,
    name: str,
    value: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Update one database parameter (two-stage).

    Args:
        instance_id: exact instance id.
        name: parameter name (e.g. max_connections).
        value: new value as string.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ParamService().update_parameter(
        instance_id=instance_id, name=name, value=value, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_configurations() -> dict[str, Any]:
    """List PostgreSQL parameter templates (custom + default)."""
    return await ParamService().list_configurations()


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def apply_pg_configuration(
    config_id: str,
    instance_ids: list[str],
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Apply a parameter template to instances (two-stage).

    Args:
        config_id: template id from list_pg_configurations.
        instance_ids: target instance ids.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ParamService().apply_configuration(
        config_id=config_id, instance_ids=instance_ids, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def compare_pg_configurations(source_id: str, target_id: str) -> dict[str, Any]:
    """Compare two parameter templates and show the parameter diffs.

    Args:
        source_id/target_id: template ids from list_pg_configurations.
    """
    return await ParamService().compare_configurations(
        source_id=source_id, target_id=target_id
    )


# --- P1-10 extensions ----------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_extensions(instance_id: str, database_name: str) -> dict[str, Any]:
    """List extensions available/installed in a database.

    Args:
        instance_id: exact instance id.
        database_name: target database.
    """
    return await ExtensionService().list_extensions(
        instance_id=instance_id, database_name=database_name
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def install_pg_extension(
    instance_id: str,
    database_name: str,
    extension_name: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Install an extension into a database (two-stage).

    Args:
        instance_id: exact instance id.
        database_name: target database.
        extension_name: e.g. pgvector, pg_stat_statements.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await ExtensionService().install_extension(
        instance_id=instance_id,
        database_name=database_name,
        extension_name=extension_name,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def uninstall_pg_extension(
    instance_id: str,
    database_name: str,
    extension_name: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Uninstall an extension from a database (two-stage)."""
    return await ExtensionService().uninstall_extension(
        instance_id=instance_id,
        database_name=database_name,
        extension_name=extension_name,
        confirm=confirm,
        plan_id=plan_id,
    )
