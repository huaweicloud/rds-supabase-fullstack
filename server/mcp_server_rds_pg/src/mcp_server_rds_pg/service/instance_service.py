# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Scenario orchestration: RDS for PostgreSQL instance lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import clamp_limit, page_result, single_result

from mcp_server_rds_pg.client.shared_client import get_shared_client

if TYPE_CHECKING:
    from mcp_server_rds_pg.client.sdk_rds import SdkRdsClient
from mcp_server_rds_pg.service.mutate import run_mutation
from mcp_server_rds_pg.service.plans import PlanStore

_INSTANCE_FIELDS = (
    "id",
    "name",
    "status",
    "current_actions",
    "datastore",
    "flavor_ref",
    "volume",
    "ha",
    "charge_info",
    "private_ips",
    "public_ips",
    "port",
    "type",
    "created",
    "updated",
    "tags",
)

_JOB_FIELDS = (
    "id",
    "name",
    "status",
    "created",
    "ended",
    "fail_reason",
    "instance",
    "entities",
)


class InstanceService:
    """Instance lifecycle scenarios: list/show, jobs, reboot/stop/start."""

    def __init__(
        self,
        client: SdkRdsClient | None = None,
        plans: PlanStore | None = None,
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def list_instances(
        self,
        *,
        name: str | None = None,
        instance_id: str | None = None,
        limit: int = 20,
        offset: int | None = None,
    ) -> dict[str, Any]:
        limit = clamp_limit(limit)
        response = await self._client.list_instances(
            limit=limit, offset=offset, id=instance_id, name=name
        )
        instances = [self._view(item) for item in response.get("instances") or []]
        total = response.get("total")
        next_offset: int | None = None
        if total is not None and instances:
            consumed = int(offset or 0) + len(instances)
            if consumed < int(total):
                next_offset = consumed
        return page_result(
            instances,
            total=int(total) if total is not None else None,
            marker=str(next_offset) if next_offset is not None else None,
        )

    async def show_instance(self, *, instance_id: str) -> dict[str, Any]:
        instances = await self._find(instance_id)
        return single_result(self._view(instances))

    async def show_job(self, *, job_id: str) -> dict[str, Any]:
        response = await self._client.list_job_info(job_id=job_id)
        job = response.get("job") or response
        if not job.get("id"):
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"Job {job_id} not found",
                hint="Job ids come from create/mutate results (job_id field).",
            )
        return single_result(
            self._pick(job, _JOB_FIELDS),
            hints=[
                "Terminal states are Completed/Failed; anything else means the job"
                " is still running - poll again."
            ],
        )

    async def reboot(
        self, *, instance_id: str, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        await self._require_found(instance_id)
        return await run_mutation(
            tool_name="reboot_pg_instance",
            instance_id=instance_id,
            operation="reboot",
            body={"instance_id": instance_id},
            notices={
                "warnings": [
                    "Rebooting interrupts all database connections for the duration"
                    " of the restart.",
                    "Prefer a low-traffic maintenance window.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.reboot_instance(instance_id=instance_id),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def stop(
        self, *, instance_id: str, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        charge_mode = await self._charge_mode(instance_id)
        if charge_mode != "postPaid":
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "Only pay-per-use (postPaid) instances can be stopped",
                hint="Yearly/monthly (prePaid) instances are always running; use the"
                " subscription console instead.",
            )
        return await run_mutation(
            tool_name="stop_pg_instance",
            instance_id=instance_id,
            operation="stop",
            body={"instance_id": instance_id},
            notices={
                "warnings": [
                    "Stopped instances still incur storage charges (compute pauses).",
                    "A stopped instance cannot be connected; start it again before use.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.stop_instance(instance_id=instance_id),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def start(
        self, *, instance_id: str, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        await self._require_found(instance_id)
        return await run_mutation(
            tool_name="start_pg_instance",
            instance_id=instance_id,
            operation="start",
            body={"instance_id": instance_id},
            notices={},
            recheck=False,  # start applies to stopped (non-ACTIVE) instances
            execute=lambda: self._client.start_instance(instance_id=instance_id),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    # -- internals ---------------------------------------------------------

    def _view(self, item: dict[str, Any]) -> dict[str, Any]:
        view = self._pick(item, _INSTANCE_FIELDS)
        view["charge_mode"] = (item.get("charge_info") or {}).get("charge_mode")
        return view

    @staticmethod
    def _pick(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
        return {key: source[key] for key in fields if source.get(key) is not None}

    async def _find(self, instance_id: str) -> dict[str, Any]:
        response = await self._client.list_instances(limit=1, offset=None, id=instance_id)
        instances = response.get("instances") or []
        if not instances or instances[0].get("id") != instance_id:
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"Instance {instance_id} not found",
                hint="Call list_pg_instances to get the exact instance id.",
            )
        engine = (instances[0].get("datastore") or {}).get("type")
        if engine and engine != "PostgreSQL":
            raise McpToolError(
                "MCP_INVALID_ARGS",
                f"Instance {instance_id} is a {engine} instance;"
                " this service only manages PostgreSQL",
                hint="PostgreSQL only; use the engine-specific service for this instance.",
            )
        return cast(dict[str, Any], instances[0])

    async def _require_found(self, instance_id: str) -> None:
        await self._find(instance_id)

    async def _charge_mode(self, instance_id: str) -> str | None:
        instance = await self._find(instance_id)
        charge_mode = (instance.get("charge_info") or {}).get("charge_mode")
        return str(charge_mode) if charge_mode is not None else None
