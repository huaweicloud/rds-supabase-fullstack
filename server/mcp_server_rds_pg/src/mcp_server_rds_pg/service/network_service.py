# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M4 services: network environment + EIP (discovery, creation, bind/unbind).

Discovery aggregates EPS + VPC + subnets + security groups into one placement
recommendation. Every write goes through run_mutation (two-phase commit),
mirroring the other scenario services.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import page_result, single_result

from mcp_server_rds_pg.client.network_apis import (
    EipChannel,
    EpsChannel,
    VpcChannel,
)
from mcp_server_rds_pg.client.shared_client import get_shared_client
from mcp_server_rds_pg.service.mutate import run_mutation
from mcp_server_rds_pg.service.plans import PlanStore

_DEFAULT_PG_PORT = 5432

_EIP_USAGE_TAG = "rds-pg"  # USAGE_FOR provenance tag, mgr parity

_EPS_NOTE_OK = (
    "EPS-enabled account: pick the enterprise project for new resources "
    "(default = the project named 'default')."
)
_EPS_NOTE_UNAVAILABLE = (
    "Enterprise project list unavailable (personal account, EPS not enabled, "
    "or missing global-service permission): omit the field - placement is "
    "then decided by the backend."
)
_EPS_NOTE_EMPTY = (
    "No enterprise projects found: omit the field - placement is decided by "
    "the backend."
)


def _cidr(value: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    try:
        return ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None


def _is_valid_cidr(value: str) -> bool:
    return _cidr(value) is not None


def _cidr_within(child: str, parent: str) -> bool:
    child_net = _cidr(child)
    parent_net = _cidr(parent)
    if child_net is None or parent_net is None:
        return False
    if not isinstance(child_net, type(parent_net)):
        return False
    if isinstance(child_net, ipaddress.IPv4Network) and isinstance(
        parent_net, ipaddress.IPv4Network
    ):
        return child_net.subnet_of(parent_net)
    if isinstance(child_net, ipaddress.IPv6Network) and isinstance(
        parent_net, ipaddress.IPv6Network
    ):
        return child_net.subnet_of(parent_net)
    return False


class NetworkService:
    """Network environment discovery and creation (VPC/subnet/SG/EPS/EIP)."""

    def __init__(
        self,
        client: SdkRdsClient | None = None,
        plans: PlanStore | None = None,
        vpc: VpcChannel | None = None,
        eip: EipChannel | None = None,
        eps: EpsChannel | None = None,
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()
        self._vpc = vpc or VpcChannel()
        self._eip = eip or EipChannel()
        self._eps = eps or EpsChannel()

    # -- discovery (READ) --------------------------------------------------

    async def discover(self) -> dict[str, Any]:
        eps = await self._eps_list_or_none()
        vpcs = await self._list_vpc_views()
        subnets = await self._list_subnet_views(vpcs)
        security_groups = await self._list_sg_views()

        default_vpc = next((v for v in vpcs if v.get("name") == "default"), None)
        default_subnet = None
        if default_vpc:
            default_subnet = next(
                (s for s in subnets if s.get("vpc_id") == default_vpc.get("id")),
                None,
            )
        open_5432_groups = [g for g in security_groups if g.get("open_5432")]
        placement = {
            "recommended_vpc": default_vpc or (vpcs[0] if vpcs else None),
            "recommended_subnet": default_subnet,
            "note": "Default VPC/subnet first (agent-default tier); creating a "
            "dedicated VPC is a user-confirm decision.",
        }
        sg_plan = {
            "strategy": "reuse first",
            "candidates_with_5432": [g["id"] for g in open_5432_groups],
            "candidates_all": [g["id"] for g in security_groups],
            "note": "Reuse an SG that already allows 5432; otherwise create one "
            "via create_pg_security_group with an explicit source CIDR.",
        }
        return single_result(
            {
                "enterprise_projects": eps,
                "vpcs": vpcs,
                "subnets": subnets,
                "security_groups": security_groups,
                "placement_recommendation": placement,
                "security_group_plan": sg_plan,
            },
            hints=[
                "Feed these facts into plan_pg_instance_creation (network module) "
                "before creating any instance.",
            ],
        )

    async def list_enterprise_projects(self) -> dict[str, Any]:
        eps = await self._eps_list_or_none()
        return single_result({"enterprise_projects": eps})

    async def list_vpcs(self) -> dict[str, Any]:
        vpcs = await self._list_vpc_views()
        return page_result(vpcs, total=len(vpcs))

    async def list_subnets(self, *, vpc_id: str) -> dict[str, Any]:
        vpcs = await self._list_vpc_views()
        target = next((v for v in vpcs if v.get("id") == vpc_id), None)
        if target is None:
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"VPC {vpc_id} not found",
                hint="Call list_pg_vpcs first and pass an exact vpc id.",
            )
        subnets = await self._list_subnet_views([target])
        return page_result(subnets, total=len(subnets))

    async def list_security_groups(self) -> dict[str, Any]:
        groups = await self._list_sg_views()
        return page_result(groups, total=len(groups))

    # -- creation (WRITE, two-phase) ----------------------------------------

    async def create_vpc(
        self,
        *,
        name: str,
        cidr: str = "192.168.0.0/16",
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        if not _is_valid_cidr(cidr):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Invalid VPC CIDR: {cidr}",
                hint="Use an IPv4 CIDR such as 192.168.0.0/16 (RFC1918 ranges).",
            )
        net = _cidr(cidr)
        assert net is not None
        if not net.is_private:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "VPC CIDR must be a private range (RFC1918)",
                hint="Use 10.0.0.0/8, 172.16.0.0/12 or 192.168.0.0/16 style ranges.",
            )
        return await run_mutation(
            tool_name="create_pg_vpc",
            instance_id=None,
            operation="create_vpc",
            body={"name": name, "cidr": cidr},
            notices={
                "warnings": [
                    "An empty VPC is free of charge but counts against the VPC quota."
                ]
            },
            recheck=False,
            execute=lambda: self._vpc.create_vpc(name=name, cidr=cidr),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_subnet(
        self,
        *,
        vpc_id: str,
        name: str,
        cidr: str,
        availability_zone: str,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        if not _is_valid_cidr(cidr):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Invalid subnet CIDR: {cidr}",
                hint="Use an IPv4 CIDR such as 192.168.0.0/24.",
            )
        vpcs = await self._list_vpc_views()
        target = next((v for v in vpcs if v.get("id") == vpc_id), None)
        if target is None:
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"VPC {vpc_id} not found",
                hint="Call list_pg_vpcs first and pass an exact vpc id.",
            )
        vpc_cidr = str(target.get("cidr") or "")
        if not vpc_cidr or not _cidr_within(cidr, vpc_cidr):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Subnet CIDR {cidr} must fall inside VPC CIDR {vpc_cidr or 'unknown'}",
                hint="Pick a sub-range of the VPC CIDR, e.g. 192.168.1.0/24 inside "
                "192.168.0.0/16.",
            )
        return await run_mutation(
            tool_name="create_pg_subnet",
            instance_id=None,
            operation="create_subnet",
            body={
                "vpc_id": vpc_id,
                "name": name,
                "cidr": cidr,
                "availability_zone": availability_zone,
            },
            notices={
                "warnings": [
                    "The subnet must live in the same availability zone as the "
                    "RDS instance that will use it.",
                    "A wrong AZ placement only surfaces at instance-creation time.",
                ]
            },
            recheck=False,
            execute=lambda: self._vpc.create_subnet(
                vpc_id=vpc_id,
                name=name,
                cidr=cidr,
                availability_zone=availability_zone,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_security_group(
        self,
        *,
        name: str,
        open_5432_from: str | None = None,
        open_5432: bool = True,
        subnet_id: str | None = None,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a security group, optionally with an ingress 5432 rule.

        Source for the 5432 rule (open_5432=true, one of three):
        - 'open'             -> 0.0.0.0/0 (internet, must be spelled out)
        - a single device IP -> /32 derived automatically
        - a custom bounded CIDR (e.g. 10.0.0.0/24)
        Default: the CIDR of the subnet named by subnet_id (bounded by design).
        open_5432=false creates an empty group (rules added manually later).
        """
        source_cidr: str | None = None
        if open_5432:
            source_cidr = await self._resolve_5432_source(
                open_5432_from, subnet_id
            )
        body: dict[str, Any] = {
            "name": name,
            "open_5432": open_5432,
            **({"open_5432_from": open_5432_from} if open_5432_from else {}),
            **({"subnet_id": subnet_id} if subnet_id else {}),
            **({"resolved_source_cidr": source_cidr} if source_cidr else {}),
        }
        warnings: list[str] = []
        if source_cidr == "0.0.0.0/0":
            warnings.append(
                "Source 0.0.0.0/0 exposes port 5432 to the entire internet - "
                "prefer a bounded CIDR."
            )
        return await run_mutation(
            tool_name="create_pg_security_group",
            instance_id=None,
            operation="create_security_group",
            body=body,
            notices={"warnings": warnings or [
                "Rules added here take effect for every instance attached to "
                "this group."
            ]},
            recheck=False,
            execute=lambda: self._do_create_security_group(
                name=name, source_cidr=source_cidr
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_enterprise_project(
        self,
        *,
        name: str,
        description: str | None = None,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="create_pg_enterprise_project",
            instance_id=None,
            operation="create_enterprise_project",
            body={"name": name, **({"description": description} if description else {})},
            notices={
                "warnings": [
                    "Creating an enterprise project requires administrator "
                    "permissions and is an organization-level resource.",
                ]
            },
            recheck=False,
            execute=lambda: self._eps.create_enterprise_project(
                name=name, description=description
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_eip(
        self,
        *,
        name: str | None,
        billing_type: str,
        bandwidth_size: int = 5,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        if billing_type not in ("traffic", "bandwidth"):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "billing_type must be 'traffic' (pay per GB) or 'bandwidth' "
                "(pay per Mbps) - a user-only billing decision",
                hint="Ask the user which billing mode fits; the Agent must not "
                "pick a default.",
            )
        if billing_type == "bandwidth" and not 1 <= bandwidth_size <= 2000:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "bandwidth_size must be 1-2000 Mbps for bandwidth billing",
            )
        alias = name or "rds-pg-eip"
        body = {
            "name": name,
            "billing_type": billing_type,
            "bandwidth_size": bandwidth_size,
            "charge_mode": "postPaid",
        }
        return await run_mutation(
            tool_name="create_pg_eip",
            instance_id=None,
            operation="create_eip",
            body=body,
            notices={
                "warnings": [
                    "The EIP is billed continuously from creation until it is "
                    "released (idle/unbound EIPs still accrue a retention fee).",
                    "billing_type is a user-only decision "
                    f"(you chose {billing_type}).",
                ]
            },
            recheck=False,
            execute=lambda: self._do_create_eip(
                alias=alias,
                charge_mode=billing_type,
                bandwidth_size=bandwidth_size,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    # -- EIP bind/unbind (DANGEROUS, two-phase, recheck) --------------------

    async def bind_eip(
        self,
        *,
        instance_id: str,
        public_ip_id: str,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        instance = await InstanceService(
            client=self._client, plans=self._plans
        )._find(instance_id)
        # Single-public-IP semantics: a bound EIP must be released from the
        # instance first, otherwise the cloud rejects with DBS.01010218.
        existing = instance.get("public_ips") or []
        if existing:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "Instance already has a public IP bound (RDS allows one at a"
                f" time): {existing[0]}",
                hint="Call unbind_pg_instance_eip first, then bind the new EIP.",
            )
        public_ip = await self._eip_address_of(public_ip_id)
        body = {"instance_id": instance_id, "public_ip_id": public_ip_id,
                "public_ip": public_ip}
        return await run_mutation(
            tool_name="bind_pg_instance_eip",
            instance_id=instance_id,
            operation="bind_eip",
            body=body,
            notices={
                "warnings": [
                    "Binding an EIP exposes the instance to the public internet - "
                    "make sure the security group only allows the intended source "
                    "IPs on port 5432.",
                    "Public traffic costs money under the EIP billing mode.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.attach_eip(
                instance_id=instance_id,
                public_ip=public_ip,
                public_ip_id=public_ip_id,
                is_bind=True,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def unbind_eip(
        self,
        *,
        instance_id: str,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        instance = await InstanceService(
            client=self._client, plans=self._plans
        )._find(instance_id)
        public_ips = instance.get("public_ips") or []
        if not public_ips:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Instance {instance_id} has no public IP to unbind",
                hint="Call show_pg_instance to check public_ips first.",
            )
        body = {"instance_id": instance_id, "public_ip": public_ips[0]}
        return await run_mutation(
            tool_name="unbind_pg_instance_eip",
            instance_id=instance_id,
            operation="unbind_eip",
            body=body,
            notices={
                "warnings": [
                    "Unbinding does NOT release the EIP and does NOT stop its "
                    "billing - release it separately when no longer needed.",
                    "Existing public connections drop immediately after unbind.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.attach_eip(
                instance_id=instance_id,
                public_ip=public_ips[0],
                public_ip_id=None,
                is_bind=False,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    # -- internals -----------------------------------------------------------

    async def _eps_list_or_none(self) -> list[dict[str, Any]] | None:
        """EPS list, degraded to None when unavailable (mgr _eps_field parity).

        Discovery must not fail as a whole just because the account is a
        personal account / EPS is not enabled.
        """
        try:
            response = await self._eps.list_enterprise_projects()
        except McpToolError:
            return None
        projects = response.get("enterprise_projects")
        if not isinstance(projects, list):
            return None
        return [
            {"id": p.get("id"), "name": p.get("name"), "status": p.get("status")}
            for p in projects
        ]

    async def _list_vpc_views(self) -> list[dict[str, Any]]:
        response = await self._vpc.list_vpcs()
        return [
            {
                "id": v.get("id"),
                "name": v.get("name"),
                "cidr": v.get("cidr"),
                "status": v.get("status"),
            }
            for v in response.get("vpcs") or []
        ]

    async def _list_subnet_views(
        self, vpcs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        views: list[dict[str, Any]] = []
        for vpc in vpcs:
            response = await self._vpc.list_subnets(vpc_id=str(vpc.get("id")))
            for s in response.get("subnets") or []:
                views.append(
                    {
                        "id": s.get("id"),
                        "name": s.get("name"),
                        "vpc_id": s.get("vpc_id"),
                        "cidr": s.get("cidr"),
                        "availability_zone": s.get("availability_zone"),
                        "gateway_ip": s.get("gateway_ip"),
                        "available_ip_address_count": s.get(
                            "available_ip_address_count"
                        ),
                    }
                )
        return views

    async def _list_sg_views(self) -> list[dict[str, Any]]:
        response = await self._vpc.list_security_groups()
        groups = response.get("security_groups") or []
        views: list[dict[str, Any]] = []
        for g in groups:
            rules = await self._sg_rules_of(str(g.get("id")))
            views.append(
                {
                    "id": g.get("id"),
                    "name": g.get("name"),
                    "description": g.get("description"),
                    "open_5432": self._allows_5432(rules),
                    "rule_count": len(rules),
                }
            )
        return views

    async def _sg_rules_of(self, security_group_id: str) -> list[dict[str, Any]]:
        try:
            response = await self._vpc.list_security_group_rules(
                security_group_id=security_group_id
            )
        except McpToolError:
            return []
        return list(response.get("security_group_rules") or [])

    @staticmethod
    def _allows_5432(rules: list[dict[str, Any]]) -> bool:
        for rule in rules:
            if str(rule.get("direction") or "") != "ingress":
                continue
            if str(rule.get("protocol") or "").lower() != "tcp":
                continue
            port = str(rule.get("multiport") or "")
            # empty multiport = all ports, which covers 5432 too
            if port and not _port_range_covers(port, _DEFAULT_PG_PORT):
                continue
            if str(rule.get("action") or "allow") != "allow":
                continue
            if rule.get("remote_ip_prefix") is None and rule.get("remote_group_id"):
                continue
            return True
        return False

    async def _resolve_5432_source(
        self, open_5432_from: str | None, subnet_id: str | None
    ) -> str | None:
        """Resolve the three-choice 5432 source into a concrete CIDR."""
        if open_5432_from is not None:
            value = open_5432_from.strip()
            if value == "open":
                return "0.0.0.0/0"
            if "/" in value:
                if not _is_valid_cidr(value):
                    raise McpToolError(
                        "MCP_INVALID_ARGS",
                        f"Invalid source CIDR: {value}",
                        hint="Use a bounded IPv4 CIDR such as 10.0.0.0/24.",
                    )
                net = _cidr(value)
                assert net is not None
                if str(net) == "0.0.0.0/0" and value != "open":
                    raise McpToolError(
                        "MCP_INVALID_ARGS",
                        "Use open_5432_from='open' to explicitly request "
                        "0.0.0.0/0 (internet-wide exposure).",
                    )
                return str(net)
            # bare IP -> /32
            try:
                ipaddress.ip_address(value)
            except ValueError as exc:
                raise McpToolError(
                    "MCP_INVALID_ARGS",
                    f"Invalid source IP: {value}",
                    hint="Provide a device IP (e.g. 1.2.3.4), a bounded CIDR "
                    "(10.0.0.0/24), or 'open' for 0.0.0.0/0.",
                ) from exc
            return f"{value}/32"
        if subnet_id:
            # default: the owning subnet's own CIDR (bounded by design)
            vpcs = await self._list_vpc_views()
            subnets = await self._list_subnet_views(vpcs)
            target = next((s for s in subnets if s.get("id") == subnet_id), None)
            if target is None:
                raise McpToolError(
                    "MCP_NOT_FOUND",
                    f"Subnet {subnet_id} not found",
                    hint="Call list_pg_subnets(vpc_id) for the exact subnet id.",
                )
            return str(target.get("cidr"))
        raise McpToolError(
            "MCP_INVALID_ARGS",
            "open_5432=true requires a source: open_5432_from ('open', an IP, or "
            "a bounded CIDR) or subnet_id (defaults to that subnet's CIDR)",
            hint="Example: create_pg_security_group(name=..., "
            "open_5432_from='10.0.0.0/24').",
        )

    async def _do_create_security_group(
        self, *, name: str, source_cidr: str | None
    ) -> dict[str, Any]:
        response = await self._vpc.create_security_group(name=name)
        group = (response.get("security_group") or {}).get("id")
        result: dict[str, Any] = {"security_group": response.get("security_group")}
        if source_cidr and group:
            # Rule creation failure degrades to a warning: the empty group
            # remains usable and rules can be added later - never an unknown
            # write result (mgr USAGE_FOR parity).
            try:
                rule = await self._vpc.create_security_group_rule(
                    security_group_id=group,
                    direction="ingress",
                    protocol="tcp",
                    multiport="5432",
                    remote_ip_prefix=source_cidr,
                    description="pg 5432 via rds-pg mcp",
                )
                result["rule"] = rule.get("security_group_rule")
            except McpToolError as exc:
                result["rule_warning"] = (
                    f"Security group created, but the 5432 rule failed: "
                    f"{exc.message} - add the rule manually or retry."
                )
        return result

    async def _do_create_eip(
        self, *, alias: str, charge_mode: str, bandwidth_size: int
    ) -> dict[str, Any]:
        response = await self._eip.create_publicip(
            alias=alias,
            charge_mode=charge_mode,
            bandwidth_size=bandwidth_size,
            bandwidth_name=f"{alias}-bw",
        )
        publicip = response.get("publicip") or {}
        result: dict[str, Any] = {"eip": publicip}
        eip_id = publicip.get("id")
        if eip_id:
            # USAGE_FOR tag is advisory provenance; failure degrades to a warning.
            try:
                await self._eip.tag_publicip(
                    publicip_id=str(eip_id), key="USAGE_FOR", value=_EIP_USAGE_TAG
                )
                result["tag"] = f"USAGE_FOR={_EIP_USAGE_TAG}"
            except McpToolError as exc:
                result["tag_warning"] = (
                    f"EIP created, but the USAGE_FOR tag failed: {exc.message} - "
                    "the tag is provenance only and can be added later."
                )
        return result

    async def _eip_address_of(self, public_ip_id: str) -> str:
        response = await self._eip.show_publicip(publicip_id=public_ip_id)
        publicip = response.get("publicip") or {}
        address = publicip.get("public_ip_address")
        if not address:
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"EIP {public_ip_id} not found or has no address",
                hint="Call list/ discover to find valid public_ip_id values.",
            )
        return str(address)


def _port_range_covers(multiport: str, port: int) -> bool:
    value = multiport.strip()
    if not value:
        return True  # empty multiport = all ports
    try:
        if "-" in value:
            low, high = value.split("-", 1)
            return int(low) <= port <= int(high)
        return int(value) == port
    except ValueError:
        return False
