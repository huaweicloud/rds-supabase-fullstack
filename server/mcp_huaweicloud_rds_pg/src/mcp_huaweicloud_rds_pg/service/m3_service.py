# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M3 services: resize, logs, parameters, extensions, monitoring (P1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import clamp_limit, page_result, single_result

from mcp_huaweicloud_rds_pg.client.m3_apis import CesClient
from mcp_huaweicloud_rds_pg.client.shared_client import get_shared_client

if TYPE_CHECKING:
    from mcp_huaweicloud_rds_pg.client.sdk_rds import SdkRdsClient
from mcp_huaweicloud_rds_pg.service.mutate import run_mutation
from mcp_huaweicloud_rds_pg.service.plans import PlanStore

_RDS_METRIC_NAMESPACE = "SYS.RDS"


class ResizeService:
    """P1-5/P1-6: flavor/volume, HA conversion, ops window, replicas."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def resize_flavor(
        self, *, instance_id: str, spec_code: str, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="resize_pg_flavor",
            instance_id=instance_id,
            operation="resize_flavor",
            body={"instance_id": instance_id, "spec_code": spec_code},
            notices={
                "warnings": [
                    "Resizing restarts the database - minutes of downtime.",
                    "Downsizing may fail if data no longer fits.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.resize_flavor(
                instance_id=instance_id, spec_code=spec_code
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def extend_volume(
        self, *, instance_id: str, size: int, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="extend_pg_volume",
            instance_id=instance_id,
            operation="extend_volume",
            body={"instance_id": instance_id, "size": size},
            notices={
                "warnings": [
                    "Storage is billed on the new size from the change onward "
                    "(no shrink of the bill).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.enlarge_volume(
                instance_id=instance_id, size=size
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def reduce_volume(
        self, *, instance_id: str, size: int, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="reduce_pg_volume",
            instance_id=instance_id,
            operation="reduce_volume",
            body={"instance_id": instance_id, "size": size},
            notices={
                "warnings": [
                    "Volume reduction requires engine 17+ and free space headroom.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.reduce_volume(
                instance_id=instance_id, size=size
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def set_auto_enlarge_policy(
        self, *, instance_id: str, switch_option: bool, limit_size: int | None,
        trigger_threshold: int | None, confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="set_pg_auto_enlarge_policy",
            instance_id=instance_id,
            operation="auto_enlarge_policy",
            body={
                "instance_id": instance_id,
                "switch_option": switch_option,
                "limit_size": limit_size,
                "trigger_threshold": trigger_threshold,
            },
            notices={},
            recheck=True,
            execute=lambda: self._client.set_auto_enlarge_policy(
                instance_id=instance_id,
                switch_option=switch_option,
                limit_size=limit_size,
                trigger_threshold=trigger_threshold,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def switch_single_to_ha(
        self, *, instance_id: str, az_code_new_node: str, confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="switch_pg_single_to_ha",
            instance_id=instance_id,
            operation="single_to_ha",
            body={"instance_id": instance_id, "az_code_new_node": az_code_new_node},
            notices={
                "warnings": [
                    "Single-to-HA conversion takes minutes and restarts the instance.",
                    "HA billing is roughly double the Single price.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.switch_single_to_ha(
                instance_id=instance_id, az_codes=[az_code_new_node]
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def change_ops_window(
        self, *, instance_id: str, start_time: str, end_time: str,
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="change_pg_ops_window",
            instance_id=instance_id,
            operation="ops_window",
            body={
                "instance_id": instance_id,
                "start_time": start_time,
                "end_time": end_time,
            },
            notices={},
            recheck=True,
            execute=lambda: self._client.change_ops_window(
                instance_id=instance_id, start_time=start_time, end_time=end_time
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_read_replicas(self, *, primary_id: str) -> dict[str, Any]:
        response = await self._client.list_instances(limit=100, offset=None)
        replicas = [
            i
            for i in response.get("instances") or []
            if (i.get("type") or "").lower() in ("replica", "readonly", "read_replica")
            or (i.get("primary_instance") or {}).get("id") == primary_id
        ]
        return page_result(replicas, total=len(replicas))


class LogService:
    """P1-8: error/slow/audit logs."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    @staticmethod
    def _normalize_log_date(raw: str) -> str:
        """Accept ISO-8601 variants; emit 'YYYY-MM-DDTHH:MM:SS+0800' for RDS."""
        from datetime import datetime, timedelta, timezone

        text = raw.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        shifted = parsed.astimezone(timezone(timedelta(hours=8)))
        return shifted.strftime("%Y-%m-%dT%H:%M:%S+0800")

    async def list_error_logs(
        self, *, instance_id: str, start_date: str, end_date: str, limit: int
    ) -> dict[str, Any]:
        limit = clamp_limit(limit)
        response = await self._client.list_error_logs(
            instance_id=instance_id,
            start_date=self._normalize_log_date(start_date),
            end_date=self._normalize_log_date(end_date),
            offset=0,
            limit=limit,
        )
        logs = response.get("error_log_list") or []
        return page_result(logs, total=response.get("total_record") or len(logs))

    async def list_slow_logs(
        self, *, instance_id: str, start_date: str, end_date: str, limit: int
    ) -> dict[str, Any]:
        limit = clamp_limit(limit)
        response = await self._client.list_slow_logs(
            instance_id=instance_id,
            start_date=self._normalize_log_date(start_date),
            end_date=self._normalize_log_date(end_date),
            offset=0,
            limit=limit,
        )
        logs = response.get("slow_log_list") or []
        return page_result(logs, total=response.get("total_record") or len(logs))

    async def download_error_log(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.download_errorlog(instance_id=instance_id)
        links = response.get("list") or response.get("errorlog_list") or []
        return page_result(links, total=len(links))

    async def download_slow_log(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.download_slowlog(instance_id=instance_id, file_name="")
        links = response.get("list") or []
        return page_result(links, total=len(links))

    async def set_auditlog_policy(
        self, *, instance_id: str, keep_days: int, confirm: bool, plan_id: str | None
    ) -> dict[str, Any]:
        if keep_days and keep_days < 0:
            raise McpToolError("MCP_INVALID_ARGS", "keep_days must be >= 0 (0 disables)")
        return await run_mutation(
            tool_name="set_pg_audit_log_policy",
            instance_id=instance_id,
            operation="auditlog_policy",
            body={"instance_id": instance_id, "keep_days": keep_days},
            notices={
                "warnings": [
                    "SQL audit logging is billed by volume once enabled - "
                    "set an explicit retention (keep_days).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.set_auditlog_policy(
                instance_id=instance_id, keep_days=keep_days
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_audit_logs(self, *, instance_id: str, limit: int) -> dict[str, Any]:
        limit = clamp_limit(limit)
        response = await self._client.list_auditlogs(
            instance_id=instance_id, limit=limit
        )
        logs = response.get("audit_logs") or []
        return page_result(logs, total=response.get("total") or len(logs))


class ParamService:
    """P1-9: parameters and configuration templates."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def show_parameters(
        self, *, instance_id: str, name: str | None
    ) -> dict[str, Any]:
        response = await self._client.show_pg_parameters(
            instance_id=instance_id, name=name
        )
        params = response.get("configurations") or []
        return page_result(params, total=response.get("total_count"))

    async def update_parameter(
        self, *, instance_id: str, name: str, value: str, confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="update_pg_parameter",
            instance_id=instance_id,
            operation="update_parameter",
            body={"instance_id": instance_id, "name": name, "value": value},
            notices={
                "warnings": [
                    "Parameters flagged restart-required only take effect after a "
                    "reboot (show_pg_parameters shows which).",
                    "Invalid values can degrade or break the database.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.update_pg_parameter(
                instance_id=instance_id, name=name, value=value
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_configurations(self) -> dict[str, Any]:
        response = await self._client.list_configurations(engine=None)
        items = [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "description": c.get("description"),
                "datastore_name": c.get("datastore_name"),
                "datastore_version_name": c.get("datastore_version_name"),
                "instance_count": c.get("instance_count"),
            }
            for c in response.get("configurations") or []
            if str(c.get("datastore_name") or "").lower() == "postgresql"
        ]
        return page_result(items, total=len(items))

    async def apply_configuration(
        self, *, config_id: str, instance_ids: list[str], confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        primary = instance_ids[0] if instance_ids else None
        return await run_mutation(
            tool_name="apply_pg_configuration",
            instance_id=primary,
            operation="apply_configuration",
            body={"config_id": config_id, "instance_ids": instance_ids},
            notices={
                "warnings": [
                    "Template parameters replace instance parameters; "
                    "restart-required entries need a reboot.",
                ]
            },
            recheck=False,
            execute=lambda: self._client.apply_configuration(
                config_id=config_id, instance_ids=instance_ids
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def compare_configurations(
        self, *, source_id: str, target_id: str
    ) -> dict[str, Any]:
        response = await self._client.compare_configurations(
            source_id=source_id, target_id=target_id
        )
        return single_result(response)


class ExtensionService:
    """P1-10: PostgreSQL extensions."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def list_extensions(
        self, *, instance_id: str, database_name: str
    ) -> dict[str, Any]:
        response = await self._client.list_pg_extensions(
            instance_id=instance_id, database_name=database_name, limit=100
        )
        items = response.get("extension_info") or response.get("extensions") or []
        return page_result(items, total=len(items))

    async def install_extension(
        self, *, instance_id: str, database_name: str, extension_name: str,
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="install_pg_extension",
            instance_id=instance_id,
            operation="install_extension",
            body={
                "instance_id": instance_id,
                "database_name": database_name,
                "extension_name": extension_name,
            },
            notices={
                "warnings": [
                    "Some extensions require a reboot before use "
                    "(check the extension list's restart flag).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.create_pg_extension(
                instance_id=instance_id,
                database_name=database_name,
                extension_name=extension_name,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def uninstall_extension(
        self, *, instance_id: str, database_name: str, extension_name: str,
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="uninstall_pg_extension",
            instance_id=instance_id,
            operation="uninstall_extension",
            body={
                "instance_id": instance_id,
                "database_name": database_name,
                "extension_name": extension_name,
            },
            notices={
                "warnings": ["Objects using the extension must be dropped first."]
            },
            recheck=True,
            execute=lambda: self._client.delete_pg_extension(
                instance_id=instance_id,
                database_name=database_name,
                extension_name=extension_name,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )


class MonitorService:
    """P1-7: CES metric data and alarm rules."""

    def __init__(
        self, client: SdkRdsClient | None = None, ces: CesClient | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._ces = ces or CesClient()

    async def show_metric_data(
        self, *, instance_id: str, metric_name: str, period: int, time_range: int
    ) -> dict[str, Any]:
        response = await self._ces.show_metric_data(
            namespace=_RDS_METRIC_NAMESPACE,
            metric_name=metric_name,
            dim_0=instance_id,
            period=period,
            time_range=time_range,
        )
        return single_result(response)

    async def create_alarm_rule(
        self, *, name: str, description: str | None, metric_name: str,
        instance_id: str, comparison_operator: str, value: float,
    ) -> dict[str, Any]:
        response = await self._ces.create_alarm(
            name=name,
            description=description,
            namespace=_RDS_METRIC_NAMESPACE,
            metric_name=metric_name,
            dim_0=instance_id,
            comparison_operator=comparison_operator,
            value=value,
        )
        return single_result(response)

    async def list_resource_metrics(self) -> dict[str, Any]:
        # The RDS metric-keys endpoint returns resource_monitoring_infos -
        # a live per-instance monitoring snapshot (cpu/memory/disk usage,
        # iops, tps/qps) rather than a metric-name catalog. Surface both the
        # snapshot and a static catalog of the common RDS PG metrics.
        response = await self._client.list_instances_resource_metrics(engine="postgresql")
        infos = response.get("resource_monitoring_infos") or []
        catalog = [
            {"metric_name": "rds001_cpu_util", "unit": "%", "desc": "CPU usage"},
            {"metric_name": "rds002_mem_util", "unit": "%", "desc": "memory usage"},
            {"metric_name": "rds080_disk_util", "unit": "%", "desc": "disk usage"},
            {"metric_name": "rds077_conn_usage", "unit": "%", "desc": "connection usage"},
            {"metric_name": "rds073_conns", "unit": "count", "desc": "active connections"},
            {"metric_name": "rds061_in_bandwidth", "unit": "byte/s", "desc": "in bandwidth"},
        ]
        return page_result(
            [
                {
                    "id": i.get("id"),
                    "name": i.get("name"),
                    "status": (i.get("instance_state") or {}).get("status"),
                    "cpu_usage": i.get("cpu_usage"),
                    "memory_usage": i.get("memory_usage"),
                    "disk_usage": i.get("disk_usage"),
                    "tps": i.get("tps"),
                    "iops": i.get("iops"),
                }
                for i in infos
            ],
            total=response.get("total_count"),
            marker=None,
        ) if infos else page_result(catalog, total=len(catalog))
