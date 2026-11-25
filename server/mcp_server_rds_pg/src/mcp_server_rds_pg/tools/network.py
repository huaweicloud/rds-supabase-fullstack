# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M4 tools: network environment + EIP (discovery, creation, bind/unbind)."""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.security import ToolRisk, guard

from mcp_server_rds_pg.server import mcp
from mcp_server_rds_pg.service.network_service import NetworkService


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def discover_pg_network() -> dict[str, Any]:
    """Discover the full network environment: EPS + VPCs + subnets + SGs.

    Scenario: before creating an RDS instance - one call returns the network
    facts, a placement recommendation (default VPC/subnet first) and a
    security-group plan (reuse groups that already allow 5432). Feeds
    plan_pg_instance_creation's network module.

    EPS list degrades to a note when the account is personal / EPS not
    enabled (placement then decided by the backend).
    """
    return await NetworkService().discover()


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_enterprise_projects() -> dict[str, Any]:
    """List enterprise projects (EPS v1, global service, cn-north-4).

    Scenario: picking the enterprise project for a new instance on an
    EPS-enabled account.
    """
    return await NetworkService().list_enterprise_projects()


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_vpcs() -> dict[str, Any]:
    """List VPCs of the region (id, name, cidr, status).

    Scenario: choosing the network placement for a new instance.
    """
    return await NetworkService().list_vpcs()


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_subnets(vpc_id: str) -> dict[str, Any]:
    """List subnets of a VPC (id, cidr, AZ, gateway, free IP count).

    Scenario: picking the subnet and matching availability zone.

    Args:
        vpc_id: exact VPC id (from list_pg_vpcs).
    """
    return await NetworkService().list_subnets(vpc_id=vpc_id)


@mcp.tool()
@guard(risk=ToolRisk.READ)
async def list_pg_security_groups() -> dict[str, Any]:
    """List security groups with an `open_5432` flag per group.

    The flag is derived from the actual ingress rules (TCP 5432 allowed).

    Scenario: deciding whether to reuse an existing group or create one.
    """
    return await NetworkService().list_security_groups()


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_vpc(
    name: str,
    cidr: str = "192.168.0.0/16",
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a VPC (two-stage; empty VPCs are free but quota-counted).

    Args:
        name: VPC name.
        cidr: IPv4 CIDR, private range (default 192.168.0.0/16).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().create_vpc(
        name=name, cidr=cidr, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_subnet(
    vpc_id: str,
    name: str,
    cidr: str,
    availability_zone: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a subnet inside a VPC (two-stage; CIDR must be inside the VPC).

    The subnet must live in the same availability zone as the instance that
    will use it.

    Args:
        vpc_id: parent VPC id.
        name: subnet name.
        cidr: IPv4 CIDR inside the VPC CIDR (e.g. 192.168.1.0/24).
        availability_zone: AZ code, e.g. cn-north-4a.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().create_subnet(
        vpc_id=vpc_id,
        name=name,
        cidr=cidr,
        availability_zone=availability_zone,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_security_group(
    name: str,
    open_5432: bool = True,
    open_5432_from: str | None = None,
    subnet_id: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create a security group, optionally with an ingress rule for 5432.

    Source for the 5432 rule (three choices, pick one):
    - open_5432_from='open' -> 0.0.0.0/0 (internet-wide; must be explicit)
    - open_5432_from='1.2.3.4' -> the device egress IP as /32
    - open_5432_from='10.0.0.0/24' -> a custom bounded CIDR
    Default (neither given): the CIDR of the subnet named by subnet_id.
    open_5432=false creates an empty group (rules added later).

    Args:
        name: security group name.
        open_5432: whether to add the ingress TCP 5432 rule.
        open_5432_from: 'open', a device IP, or a bounded CIDR.
        subnet_id: subnet whose CIDR becomes the rule source (default source).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().create_security_group(
        name=name,
        open_5432=open_5432,
        open_5432_from=open_5432_from,
        subnet_id=subnet_id,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_enterprise_project(
    name: str,
    description: str | None = None,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create an enterprise project (two-stage; admin permission required).

    Organization-level resource - only usable on EPS-enabled accounts.

    Args:
        name: enterprise project name.
        description: optional description.
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().create_enterprise_project(
        name=name, description=description, confirm=confirm, plan_id=plan_id
    )


@mcp.tool()
@guard(risk=ToolRisk.WRITE)
async def create_pg_eip(
    billing_type: str,
    name: str | None = None,
    bandwidth_size: int = 5,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Create an EIP with dedicated bandwidth (two-stage; post-paid only).

    billing_type is a user-only decision:
    - 'traffic'  - pay per GB transferred (cheapest for light use)
    - 'bandwidth'- pay per Mbps (bandwidth_size, 1-2000)

    The EIP is billed from creation until released (idle EIPs still accrue a
    retention fee). A USAGE_FOR=rds-pg provenance tag is added automatically.

    Args:
        billing_type: 'traffic' or 'bandwidth' (user-only decision).
        name: optional alias (default rds-pg-eip).
        bandwidth_size: Mbps, used with bandwidth billing (default 5).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().create_eip(
        name=name,
        billing_type=billing_type,
        bandwidth_size=bandwidth_size,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def bind_pg_instance_eip(
    instance_id: str,
    public_ip_id: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Bind an EIP to an instance (two-stage; exposes it to the internet).

    The instance must be ACTIVE with no current actions. The public IP
    address is looked up from the EIP id automatically.

    Args:
        instance_id: exact instance id.
        public_ip_id: EIP id to bind (from create_pg_eip or an existing one).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().bind_eip(
        instance_id=instance_id,
        public_ip_id=public_ip_id,
        confirm=confirm,
        plan_id=plan_id,
    )


@mcp.tool()
@guard(risk=ToolRisk.DANGEROUS)
async def unbind_pg_instance_eip(
    instance_id: str,
    confirm: bool = False,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Unbind the instance's EIP (two-stage; does NOT stop EIP billing).

    The EIP stays allocated and keeps charging until released separately.

    Args:
        instance_id: exact instance id (must currently have a public IP).
        confirm: stage-2 flag.
        plan_id: plan from the preview call.
    """
    return await NetworkService().unbind_eip(
        instance_id=instance_id, confirm=confirm, plan_id=plan_id
    )
