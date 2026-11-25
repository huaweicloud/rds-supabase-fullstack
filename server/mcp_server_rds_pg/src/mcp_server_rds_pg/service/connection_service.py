# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 services: connection management (P0-2).

Connection info, SSL cert links, port change, security-group swap,
pg_hba listing and modification.
"""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import page_result, single_result

from mcp_server_rds_pg.client.shared_client import get_shared_client
from mcp_server_rds_pg.service.mutate import run_mutation
from mcp_server_rds_pg.service.plans import PlanStore

_HBA_FIELDS = ("type", "database", "user", "address", "mask", "method", "priority")


class ConnectionService:
    """P0-2 scenarios: connect info, SSL, port, SG, pg_hba."""

    def __init__(
        self,
        client: SdkRdsClient | None = None,
        plans: PlanStore | None = None,
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def _find_managed_guard(self, instance_id: str) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        return await InstanceService(
            client=self._client, plans=self._plans
        )._find(instance_id)

    async def show_connection_info(self, *, instance_id: str) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        instance = await InstanceService(client=self._client, plans=self._plans)._find(
            instance_id
        )
        dns: dict[str, Any] | None = None
        try:
            dns = await self._client.show_dns_name(instance_id=instance_id)
        except Exception:
            # DNS capability unavailable in this region - degrade to the
            # IP-only view (the domain is optional connection info).
            dns = None
        return single_result(
            {
                "instance_id": instance_id,
                "instance_name": instance.get("name"),
                "status": instance.get("status"),
                "private_ips": instance.get("private_ips") or [],
                "public_ips": instance.get("public_ips") or [],
                "port": instance.get("port"),
                "ha": instance.get("ha"),
                "dns_name": (dns or {}).get("dns_name"),
            },
            hints=[
                "psql: psql --no-readline -h <private_ip or dns_name> -p <port> "
                "dbname=postgres user=root",
                "Use download_pg_ssl_cert for encrypted connections "
                "(sslmode=verify-ca).",
                "If dns_name is set, the intranet domain can replace the"
                " private IP in connection strings.",
            ],
        )

    async def download_ssl_cert(self, *, instance_id: str) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        await InstanceService(client=self._client, plans=self._plans)._require_found(
            instance_id
        )
        response = await self._client.list_ssl_cert_download_link(
            instance_id=instance_id
        )
        certs = response.get("cert_info_list") or []
        link = certs[0].get("download_link") if certs else None
        if not link:
            raise McpToolError(
                "MCP_NOT_FOUND",
                "No SSL cert download link available for this instance",
            )
        return single_result(
            {
                "instance_id": instance_id,
                "download_link": link,
                "category": certs[0].get("category"),
            },
            hints=[
                "Temporary URL - download promptly, it expires.",
                "ca.pem for sslmode=verify-ca; ca-bundle.pem contains both roots.",
            ],
        )

    async def change_port(
        self, *, instance_id: str, port: int, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        if not 1 <= port <= 65535:
            raise McpToolError("MCP_INVALID_ARGS", "port must be 1-65535")
        return await run_mutation(
            tool_name="change_pg_instance_port",
            instance_id=instance_id,
            operation="change_port",
            body={"instance_id": instance_id, "port": port},
            notices={
                "warnings": [
                    "Port change restarts the database - 4-10 minutes of downtime.",
                    "All clients must switch to the new port afterwards.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.update_port(instance_id=instance_id, port=port),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def change_security_group(
        self, *, instance_id: str, security_group_id: str, confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        # Supabase-managed guard: the full-replacement semantics would strip
        # the mgr-created dedicated groups (supabase-db-sg et al.), breaking
        # the hosted application. Block hard before any preview/claim.
        instance = await self._find_managed_guard(instance_id)
        # instance detail carries security_group info; detect supabase naming
        sg_list = instance.get("security_group_list") or instance.get("security_group") or []
        names = []
        if isinstance(sg_list, dict):
            names = [str(sg_list.get("name") or "")]
        elif isinstance(sg_list, list):
            names = [str(g.get("name") or "") for g in sg_list]
        if any("supabase" in n.lower() for n in names if n):
            raise McpToolError(
                "MCP_GUARDRAIL_BLOCKED",
                "Instance appears Supabase-managed (dedicated security group"
                " detected); full SG replacement would break the hosted"
                " application",
                hint="Use the Supabase management-plane tools"
                " (change_supabase_security_group, which preserves the"
                " dedicated groups) instead.",
            )
        return await run_mutation(
            tool_name="change_pg_security_group",
            instance_id=instance_id,
            operation="change_security_group",
            body={"instance_id": instance_id, "security_group_id": security_group_id},
            notices={
                "warnings": [
                    "The new security group REPLACES the current one entirely - "
                    "its rules define all database access from this moment on.",
                    "Verify the target group opens the DB port (5432 or custom).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.set_security_group(
                instance_id=instance_id, security_group_id=security_group_id
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_dns_name(
        self, *, instance_id: str, dns_type: str = "private", confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        if dns_type != "private":
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Unsupported dns_type: {dns_type!r}",
                hint="Only 'private' (intranet domain) is supported.",
            )
        return await run_mutation(
            tool_name="create_pg_dns_name",
            instance_id=instance_id,
            operation="create_dns_name",
            body={"instance_id": instance_id, "dns_type": dns_type},
            notices={
                "warnings": [
                    "Enabling the intranet DNS name takes effect only while the"
                    " instance is in the same VPC/subnet - applications connect"
                    " via the domain instead of the private IP afterwards.",
                    "The domain requires the instance to be ACTIVE with no"
                    " in-flight actions.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.create_dns_name(
                instance_id=instance_id, dns_type=dns_type
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def change_dns_name(
        self, *, instance_id: str, dns_name: str, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        import re

        if not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", dns_name or ""):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "dns_name must be lowercase letters, digits and hyphens"
                " (no leading/trailing hyphen)",
                hint="Example: e2e-test-db",
            )
        return await run_mutation(
            tool_name="update_pg_dns_name",
            instance_id=instance_id,
            operation="update_dns_name",
            body={"instance_id": instance_id, "dns_name": dns_name},
            notices={
                "warnings": [
                    "The OLD domain name stops resolving IMMEDIATELY after the"
                    " change - any connection string that still uses the old"
                    " domain will break; notify the application owners before"
                    " submitting.",
                    "The new custom name must follow the DNS naming rules"
                    " (lowercase letters, digits, hyphens).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.update_dns_name(
                instance_id=instance_id, dns_name=dns_name
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def show_dns_name(self, *, instance_id: str) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        await InstanceService(client=self._client, plans=self._plans)._require_found(
            instance_id
        )
        response = await self._client.show_dns_name(instance_id=instance_id)
        return single_result(
            {
                "instance_id": instance_id,
                "dns_name": response.get("dns_name"),
                "dns_type": response.get("dns_type"),
                "status": response.get("status"),
                "ipv6_address": response.get("ipv6_address"),
                "object_id": response.get("object_id"),
            },
            hints=[
                "Empty dns_name means the intranet DNS name is not enabled"
                " - create_pg_dns_name enables it.",
                "After update_pg_dns_name the old domain stops resolving"
                " immediately.",
            ],
        )

    async def list_hba_conf(self, *, instance_id: str) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        await InstanceService(client=self._client, plans=self._plans)._require_found(
            instance_id
        )
        response = await self._client.list_postgresql_hba_info(
            instance_id=instance_id
        )
        entries = response.get("hba_entries") or response.get("hba") or []
        items = [
            {k: e.get(k) for k in _HBA_FIELDS if e.get(k) is not None} for e in entries
        ]
        return page_result(items, total=len(items))

    async def change_hba_conf(
        self,
        *,
        instance_id: str,
        entries: list[dict[str, Any]],
        confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        for entry in entries:
            missing = {"type", "database", "user", "address", "method"} - set(entry)
            if missing:
                raise McpToolError(
                    "MCP_INVALID_ARGS",
                    f"hba entry missing required fields: {sorted(missing)}",
                    hint="Each entry needs type/database/user/address/mask/method; "
                    "priority 0-10000 (smaller = earlier).",
                )
        return await run_mutation(
            tool_name="change_pg_hba_conf",
            instance_id=instance_id,
            operation="change_hba",
            body={"instance_id": instance_id, "entries": entries},
            notices={
                "warnings": [
                    "Client authentication rules change immediately for new "
                    "connections; mistakes can lock out all clients.",
                    "Keep a psql session open in the public cloud while testing.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.add_postgresql_hba_conf(
                instance_id=instance_id, entries=entries
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )
