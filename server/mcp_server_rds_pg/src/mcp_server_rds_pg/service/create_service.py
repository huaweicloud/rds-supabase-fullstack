# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 services: catalog reads, creation orchestration, admin password reset."""

from __future__ import annotations

from typing import Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import page_result, single_result

from mcp_server_rds_pg.client.sdk_rds import SdkRdsClient
from mcp_server_rds_pg.service.mutate import run_mutation
from mcp_server_rds_pg.service.plans import PlanStore
from mcp_server_rds_pg.service.request_refs import read_request

_CREATE_FIELDS = (
    "name",
    "datastore",
    "ha",
    "port",
    "password_ref",
    "backup_strategy",
    "flavor_ref",
    "volume",
    "region",
    "availability_zone",
    "vpc_id",
    "subnet_id",
    "security_group_id",
    "charge_info",
)


class CatalogService:
    """Creation-planning reads: flavors, datastores, storage types, quotas."""

    def __init__(self, client: SdkRdsClient | None = None) -> None:
        self._client = client or SdkRdsClient()

    async def list_flavors(
        self, *, version: str, availability_zone: str | None = None
    ) -> dict[str, Any]:
        response = await self._client.list_flavors(
            version=version, availability_zone=availability_zone
        )
        flavors = response.get("flavors") or []
        items = [
            {
                "spec_code": f.get("spec_code"),
                "vcpus": f.get("vcpus"),
                "ram": f.get("ram"),
                "az_descs": [
                    d.get("az_code")
                    for d in (f.get("az_descs") or [])[:2]
                ],
            }
            for f in flavors[:100]
        ]
        return page_result(items, total=len(items))

    async def list_datastores(self) -> dict[str, Any]:
        response = await self._client.list_datastores()
        stores = response.get("data_stores") or []
        versions = [s.get("name") for s in stores if s.get("name")]
        return single_result(
            {
                "engine": "PostgreSQL",
                "versions": versions,
                "latest": versions[0] if versions else None,
            },
            hints=["RDS returns newest first; the first entry is the recommended version."],
        )

    async def list_storage_types(self, *, version: str, ha_mode: str) -> dict[str, Any]:
        response = await self._client.list_storage_types(version=version, ha_mode=ha_mode)
        return single_result(
            {
                "storage_type": response.get("storage_type"),
                "support_compute_group": response.get("support_compute_group") or [],
                "datastores_version": response.get("datastores_version") or [],
            }
        )

    async def show_quotas(self) -> dict[str, Any]:
        response = await self._client.show_quotas()
        return single_result(response.get("quotas") or response)


class CreationService:
    """Two-stage instance creation (plan -> confirm) and password reset."""

    def __init__(
        self,
        client: SdkRdsClient | None = None,
        plans: PlanStore | None = None,
        catalog: CatalogService | None = None,
    ) -> None:
        self._client = client or SdkRdsClient()
        self._plans = plans or PlanStore()
        self._catalog = catalog or CatalogService(client=self._client)

    async def plan_creation(
        self,
        *,
        needs_public_access: bool = False,
        flavor_hint: str | None = None,
    ) -> dict[str, Any]:
        """READ orchestration: live baseline + decision checklist + apply steps.

        Charge mode / EIP billing / replica count are user-only decisions;
        flavor / volume / HA get a recommendation the user confirms.
        """
        datastores = await self._catalog.list_datastores()
        version = (datastores.get("latest")) or "16"
        flavors = await self._catalog.list_flavors(version=version)
        items = flavors.get("items") or []
        recommended = next(
            (f for f in items if flavor_hint and flavor_hint in str(f.get("spec_code"))),
            None,
        )
        if recommended is None and items:
            # smallest flavor group as a safe default recommendation
            recommended = items[0]
        baseline = {
            "datastore": {"type": "PostgreSQL", "version": version},
            "flavor": recommended,
            "volume": {"type": "CLOUDSSD", "size": 40,
                       "note": "CLOUDSSD default; adjust per workload"},
            "ha": {"mode": "Ha", "replication_mode": "async"},
            "port": 5432,
            "charge_mode": "postPaid",
            "public_access": needs_public_access,
        }
        checklist = {
            "charge_mode": {
                "level": "user-only",
                "options": ["postPaid", "prePaid"],
                "note": "prePaid needs period (month/year) and auto-renew choice; "
                "billing decision the agent must not make.",
            },
            "eip_billing": {
                "level": "user-only",
                "options": ["bandwidth 5-1000Mbps", "traffic (peak-limited)"],
                "when": "needs_public_access=true",
            },
            "flavor": {"level": "user-confirm", "recommended": recommended},
            "volume": {"level": "user-confirm", "recommended": baseline["volume"]},
            "ha_mode": {"level": "user-confirm", "recommended": "Ha"},
        }
        steps = [
            {
                "step": 1,
                "phase": "request_file",
                "tool": "write_pg_secret_request",
                "action": "Store the admin password locally; use the returned request_ref.",
            },
            {
                "step": 2,
                "phase": "create",
                "tool": "create_pg_instance",
                "args": {"confirm": False},
                "note": "Preview returns plan_id; present changes+warnings to the user.",
            },
            {
                "step": 3,
                "phase": "create",
                "tool": "create_pg_instance",
                "args": {"confirm": True, "plan_id": "<step 2>"},
                "note": "Async job; poll show_pg_instance_job (5-25 min).",
            },
            {
                "step": 4,
                "phase": "verify",
                "tool": "show_pg_instance",
                "note": "status ACTIVE and no current_actions before further operations.",
            },
        ]
        if needs_public_access:
            steps.append(
                {
                    "step": 5,
                    "phase": "eip",
                    "tool": "bind_pg_instance_eip",
                    "when": "instance ACTIVE",
                    "note": "M2 follow-up; billing method is user-only.",
                }
            )
        return single_result(
            {
                "baseline": baseline,
                "decision_checklist": checklist,
                "apply_steps": steps,
                "flavor_options": items[:20],
            }
        )

    async def create_instance(
        self,
        *,
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
        charge_mode: str = "postPaid",
        period: int | None = None,
        confirm: bool = False,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        secrets = read_request(admin_password_ref)
        password = secrets.get("password")
        if not password:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "Request file lacks the password field",
            )
        if charge_mode == "prePaid" and period is None:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "prePaid requires a period (months); this is a user-only billing decision",
            )
        if ha_mode == "Ha":
            azs = [az.strip() for az in availability_zone.split(",") if az.strip()]
            if len(azs) < 2:
                raise McpToolError(
                    "MCP_INVALID_ARGS",
                    "Ha mode requires two AZs in availability_zone: 'primaryAz,standbyAz'",
                    hint="Get normal-status AZs for the flavor from list_pg_flavors "
                    "(az_status), e.g. 'cn-north-4a,cn-north-4g'.",
                )
            ha_body: dict[str, Any] | None = {
                "mode": "Ha",
                "replication_mode": "async",
            }
        else:
            ha_body = None
        body: dict[str, Any] = {
            "name": name,
            "datastore": {"type": "PostgreSQL", "version": version},
            "flavor_ref": flavor_ref,
            "volume": {"type": volume_type, "size": volume_size},
            "availability_zone": availability_zone,
            "password": password,
            "ha": ha_body,
            "port": str(port),
            "region": region,
            "charge_info": {
                "charge_mode": charge_mode,
                **({"period": period} if charge_mode == "prePaid" and period else {}),
            },
            **({"vpc_id": vpc_id} if vpc_id else {}),
            **({"subnet_id": subnet_id} if subnet_id else {}),
            **({"security_group_id": security_group_id} if security_group_id else {}),
        }
        preview_body = {k: v for k, v in body.items()}
        preview_body["password"] = "<from request_ref>"
        notices = {
            "warnings": [
                "Instance creation is billed from the moment it starts "
                "(postPaid: hourly; prePaid: whole period, no partial refund).",
                "Creation takes 5-25 minutes; accepted != complete - poll the job.",
            ]
        }
        return await run_mutation(
            tool_name="create_pg_instance",
            instance_id=None,
            operation="create",
            body=preview_body,
            notices=notices,
            recheck=False,
            execute=lambda: self._client.create_instance(body=body),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def reset_admin_password(
        self,
        *,
        instance_id: str,
        password_ref: str,
        confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        from mcp_server_rds_pg.service.instance_service import InstanceService

        await InstanceService(client=self._client, plans=self._plans)._require_found(
            instance_id
        )
        secrets = read_request(password_ref)
        password = secrets.get("password")
        if not password:
            raise McpToolError("MCP_INVALID_ARGS", "Request file lacks the password field")
        preview_body = {"instance_id": instance_id, "password_ref": password_ref}
        notices = {
            "warnings": [
                "Old sessions and automation using the previous password stop "
                "working once the change lands.",
            ]
        }
        return await run_mutation(
            tool_name="reset_pg_admin_password",
            instance_id=instance_id,
            operation="reset_password",
            body=preview_body,
            notices=notices,
            recheck=True,
            execute=lambda: self._client.reset_admin_password(
                instance_id=instance_id, password=password
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )
