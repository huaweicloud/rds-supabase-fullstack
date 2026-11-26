# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 tools: backup management (P0-3) and databases/accounts (P0-4).

Offsite backup policy deferred to follow-up (cross-region storage fee model
needs explicit user sign-off). Restore operations are out of scope by
decision. revoke_pg_db_privilege deferred (grant readonly=false covers the
common path; explicit revoke arrives with audit feedback).
"""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_huaweicloud_rds_pg.server import mcp
from mcp_huaweicloud_rds_pg.service.backup_db_service import (
    BackupService,
    PgDatabaseService,
)

# --- P0-3 backup ------------------------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_backup_policy(instance_id: str) -> dict[str, Any]:
    """Show the backup policy of an instance (retention, window, period).

    Args:
        instance_id: exact instance id.
    """
    return await BackupService().show_policy(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def set_pg_backup_policy(
    instance_id: str,
    keep_days: int,
    start_time: str,
    period: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Set the instance backup policy (two-stage).

    Args:
        instance_id: exact instance id.
        keep_days: retention days (>= 7).
        start_time: backup window, e.g. "21:00-22:00" (no timezone suffix).
        period: backup days, "1,2,3,4,5,6,7" or comma subset.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await BackupService().set_policy(
        instance_id=instance_id,
        keep_days=keep_days,
        start_time=start_time,
        period=period,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_manual_backup(
    instance_id: str,
    name: str,
    description: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a manual backup of an instance (two-stage).

    Args:
        instance_id: exact instance id.
        name: backup name.
        description: optional description.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await BackupService().create_manual_backup(
        instance_id=instance_id,
        name=name,
        description=description,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_backups(
    instance_id: str,
    backup_type: str | None = None,
    limit: int = 20,
    offset: int | None = None,
) -> dict[str, Any]:
    """List backups of an instance (auto/manual/incremental by type).

    Args:
        instance_id: exact instance id.
        backup_type: optional filter - "auto" | "manual".
        limit: page size 1-100.
        offset: page offset.
    """
    return await BackupService().list_backups(
        instance_id=instance_id,
        backup_type=backup_type,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_backup_download_link(backup_id: str) -> dict[str, Any]:
    """Get the temporary download link of a backup file.

    Args:
        backup_id: backup id from list_pg_backups.
    """
    return await BackupService().download_backup(backup_id=backup_id)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_restore_times(instance_id: str) -> dict[str, Any]:
    """List the point-in-time restore windows of an instance.

    Informational (restore operations themselves are out of scope).
    """
    return await BackupService().list_restore_times(instance_id=instance_id)


# --- P0-4 databases and accounts --------------------------------------------


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_databases(instance_id: str) -> dict[str, Any]:
    """List databases in a PG instance."""
    return await PgDatabaseService().list_databases(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_database(
    instance_id: str,
    name: str,
    owner: str | None = None,
    character_set: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a database in a PG instance (two-stage).

    Args:
        instance_id: exact instance id.
        name: database name.
        owner: owning user (defaults to root).
        character_set: e.g. UTF8 (instance default when omitted).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await PgDatabaseService().create_database(
        instance_id=instance_id,
        name=name,
        owner=owner,
        character_set=character_set,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_schemas(instance_id: str, db_name: str) -> dict[str, Any]:
    """List schemas in a database."""
    return await PgDatabaseService().list_schemas(
        instance_id=instance_id, db_name=db_name
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_schema(
    instance_id: str,
    db_name: str,
    schema_name: str,
    owner: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a schema in a database (two-stage)."""
    return await PgDatabaseService().create_schema(
        instance_id=instance_id,
        db_name=db_name,
        schema_name=schema_name,
        owner=owner,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_db_users(instance_id: str) -> dict[str, Any]:
    """List database users of an instance."""
    return await PgDatabaseService().list_users(instance_id=instance_id)


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_db_user(
    instance_id: str,
    name: str,
    password_ref: str,
    comment: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a database user (two-stage; password via request file).

    Args:
        instance_id: exact instance id.
        name: user name.
        password_ref: request file path from write_pg_secret_request.
        comment: optional remark.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await PgDatabaseService().create_user(
        instance_id=instance_id,
        name=name,
        password_ref=password_ref,
        comment=comment,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def set_pg_db_user_password(
    instance_id: str,
    name: str,
    password_ref: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Change a database user's password (two-stage; password via request file)."""
    return await PgDatabaseService().set_user_password(
        instance_id=instance_id,
        name=name,
        password_ref=password_ref,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def update_pg_db_user_comment(
    instance_id: str, name: str, comment: str, confirm: bool = False
) -> dict[str, Any]:
    """Update a database user's remark (light write; middleware confirm)."""
    return await PgDatabaseService().update_user_comment(
        instance_id=instance_id, name=name, comment=comment
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def grant_pg_db_privilege(
    instance_id: str,
    db_name: str,
    users: list[dict[str, Any]],
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Grant database privileges to users (two-stage).

    Args:
        instance_id: exact instance id.
        db_name: target database.
        users: list of {name, readonly, schema_name?}; readonly=true grants
            read-only, false grants read-write.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await PgDatabaseService().grant_privilege(
        instance_id=instance_id,
        db_name=db_name,
        users=users,
        confirm=confirm,
        plan_id=plan_id,
    )
