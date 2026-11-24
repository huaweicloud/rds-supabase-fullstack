# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 tools: catalog reads, creation orchestration, secret requests."""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_server_rds_pg.server import mcp
from mcp_server_rds_pg.service.create_service import (
    CatalogService,
    CreationService,
)
from mcp_server_rds_pg.service.request_refs import write_request


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_flavors(
    version: str, availability_zone: str | None = None
) -> dict[str, Any]:
    """List PostgreSQL instance flavors (spec codes) for a version.

    Scenario: sizing a new instance or a resize - what vCPU/RAM shapes exist.

    Args:
        version: PostgreSQL engine version (from list_pg_datastores).
        availability_zone: optional AZ filter.

    Returns:
        Paginated flavor summaries (spec_code, vcpus, ram, az).
    """
    return await CatalogService().list_flavors(
        version=version, availability_zone=availability_zone
    )


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_datastores() -> dict[str, Any]:
    """List supported PostgreSQL engine versions (newest first).

    Scenario: picking the engine version when creating an instance.
    """
    return await CatalogService().list_datastores()


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_storage_types(version: str, ha_mode: str) -> dict[str, Any]:
    """List storage (disk) types available for a PG version and HA mode.

    Scenario: choosing volume type when creating an instance.
    """
    return await CatalogService().list_storage_types(version=version, ha_mode=ha_mode)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def show_pg_quotas() -> dict[str, Any]:
    """Show RDS instance/resource quotas for the account.

    Scenario: pre-check before creating instances (quota exhaustion fails at
    create time with a confusing error).
    """
    return await CatalogService().show_quotas()


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def plan_pg_instance_creation(
    needs_public_access: bool = False, flavor_hint: str | None = None
) -> dict[str, Any]:
    """Plan a new RDS for PostgreSQL instance: live baseline + decision checklist.

    Read-only orchestration. Returns recommended baseline (engine version,
    flavor, volume, HA), a decision checklist with confirmation levels
    (user-only billing items vs user-confirm technical items), and numbered
    apply steps. Present the checklist to the user before calling
    create_pg_instance.

    Args:
        needs_public_access: include the EIP binding step in the plan.
        flavor_hint: optional substring to preselect a recommended flavor.
    """
    return await CreationService().plan_creation(
        needs_public_access=needs_public_access, flavor_hint=flavor_hint
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def write_pg_secret_request(password: str) -> dict[str, Any]:
    """Store a secret (instance/db password) in a local 0600 request file.

    The tool returns a request_ref path; pass it to create/reset tools
    instead of the plaintext password. The value never enters tool results,
    previews, or audit logs.

    Args:
        password: the secret value (kept local, never echoed back).
    """
    return write_request({"password": password})


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def create_pg_instance(
    name: str,
    flavor_ref: str,
    volume_type: str,
    volume_size: int,
    admin_password_ref: str,
    version: str,
    availability_zone: str,
    region: str,
    vpc_id: str | None = None,
    subnet_id: str | None = None,
    security_group_id: str | None = None,
    ha_mode: str = "Ha",
    port: int = 5432,
    replica_of_id: str | None = None,
    charge_mode: str = "postPaid",
    period: int | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create an RDS for PostgreSQL instance (two-stage, billed from creation).

    Stage 1: confirm=false preview (plan_id). Stage 2: same args + confirm=true.
    The admin password is provided via a request file from
    write_pg_secret_request, never in plaintext.

    prePaid requires an explicit period (months) - a user-only billing choice.

    Args:
        name: instance name.
        flavor_ref: spec code from list_pg_flavors.
        volume_type: disk type from list_pg_storage_types.
        volume_size: disk size GB.
        admin_password_ref: request file path from write_pg_secret_request.
        version: PG engine version.
        availability_zone: AZ code(s); Ha mode requires 'primaryAz,standbyAz'
            (normal-status AZs from list_pg_flavors az_status).
        region: region code, e.g. cn-north-4.
        vpc_id/subnet_id: network placement (defaults when omitted).
        security_group_id: existing SG to attach.
        ha_mode: Ha (primary/standby) or Single.
        port: database port (default 5432).
        charge_mode: postPaid | prePaid.
        period: required for prePaid (months).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await CreationService().create_instance(
        name=name,
        flavor_ref=flavor_ref,
        volume_type=volume_type,
        volume_size=volume_size,
        admin_password_ref=admin_password_ref,
        version=version,
        availability_zone=availability_zone,
        region=region,
        vpc_id=vpc_id,
        subnet_id=subnet_id,
        security_group_id=security_group_id,
        ha_mode=ha_mode,
        port=port,
        replica_of_id=replica_of_id,
        charge_mode=charge_mode,
        period=period,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def reset_pg_admin_password(
    instance_id: str,
    password_ref: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Reset the administrator (root) password of a PG instance (two-stage).

    Args:
        instance_id: exact instance id.
        password_ref: request file path from write_pg_secret_request.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await CreationService().reset_admin_password(
        instance_id=instance_id,
        password_ref=password_ref,
        confirm=confirm,
        plan_id=plan_id,
    )
