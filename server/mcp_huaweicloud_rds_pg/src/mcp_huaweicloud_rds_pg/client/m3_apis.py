# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""P1 client APIs: resize/replica, logs, parameters, extensions, CES monitoring."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException


def _to_dict(obj: Any) -> Any:
    from mcp_huaweicloud_rds_pg.client.sdk_rds import sdk_to_dict

    return sdk_to_dict(obj)


def _log_response_error(api: str, exc: Exception) -> Any:
    """Convert SDK deserialization failures on the RDS log endpoints.

    /v3/{project}/instances/{id}/error-log and /slow-log return a
    non-standard payload (XML/text for PostgreSQL) that the SDK's model
    deserializer cannot bind - the failure escapes as non-SdkException
    (AttributeError/TypeError) and previously crashed the tool. Surface a
    clear envelope telling the agent to use the download links instead.
    """
    from huaweicloud_mcp_core.errors import McpToolError

    return McpToolError(
        "MCP_SDK_DESERIALIZE",
        f"{api}: the RDS log endpoint returned a payload the SDK cannot"
        " deserialize ({type(exc).__name__}: {exc})",
        hint=(
            "This endpoint is known to return XML/text for PostgreSQL."
            " Use download_pg_error_log / download_pg_slow_log (which"
            " return download links) or the LTS variants instead."
        ),
    )


class ResizeMixin:
    """P1-5/P1-6: flavor/volume resize, HA conversion, ops window, replicas."""

    _client: Any

    async def resize_flavor(
        self, *, instance_id: str, spec_code: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.resize_flavor_object import ResizeFlavorObject
            from huaweicloudsdkrds.v3.model.resize_flavor_request import ResizeFlavorRequest
            from huaweicloudsdkrds.v3.model.start_resize_flavor_action_request import (
                StartResizeFlavorActionRequest,
            )

            body = ResizeFlavorRequest(resize_flavor=ResizeFlavorObject(spec_code=spec_code))
            request = StartResizeFlavorActionRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.start_resize_flavor_action(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def enlarge_volume(
        self, *, instance_id: str, size: int
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.enlarge_volume_object import EnlargeVolumeObject
            from huaweicloudsdkrds.v3.model.enlarge_volume_request_body import (
                EnlargeVolumeRequestBody,
            )
            from huaweicloudsdkrds.v3.model.start_instance_enlarge_volume_action_request import (
                StartInstanceEnlargeVolumeActionRequest,
            )

            body = EnlargeVolumeRequestBody(
                enlarge_volume=EnlargeVolumeObject(size=str(size))
            )
            request = StartInstanceEnlargeVolumeActionRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.start_instance_enlarge_volume_action(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def reduce_volume(
        self, *, instance_id: str, size: int
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.reduce_volume_object import ReduceVolumeObject
            from huaweicloudsdkrds.v3.model.reduce_volume_request_body import (
                ReduceVolumeRequestBody,
            )
            from huaweicloudsdkrds.v3.model.start_instance_reduce_volume_action_request import (
                StartInstanceReduceVolumeActionRequest,
            )

            body = ReduceVolumeRequestBody(
                reduce_volume=ReduceVolumeObject(size=str(size))
            )
            request = StartInstanceReduceVolumeActionRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.start_instance_reduce_volume_action(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def set_auto_enlarge_policy(
        self,
        *,
        instance_id: str,
        switch_option: bool,
        limit_size: int | None = None,
        trigger_threshold: int | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.customer_modify_auto_enlarge_policy_req import (
                CustomerModifyAutoEnlargePolicyReq,
            )
            from huaweicloudsdkrds.v3.model.set_auto_enlarge_policy_request import (
                SetAutoEnlargePolicyRequest,
            )

            body = CustomerModifyAutoEnlargePolicyReq(
                switch_option=switch_option,
                limit_size=str(limit_size) if limit_size is not None else None,
                trigger_threshold=trigger_threshold,
            )
            request = SetAutoEnlargePolicyRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.set_auto_enlarge_policy(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def switch_single_to_ha(
        self, *, instance_id: str, az_codes: list[str]
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.single2_ha import Single2Ha
            from huaweicloudsdkrds.v3.model.single2_ha_object import Single2HaObject
            from huaweicloudsdkrds.v3.model.start_instance_single_to_ha_action_request import (
                StartInstanceSingleToHaActionRequest,
            )

            body = Single2Ha(single_to_ha=Single2HaObject(az_code_new_node=az_codes[0]))
            request = StartInstanceSingleToHaActionRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.start_instance_single_to_ha_action(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def change_ops_window(
        self, *, instance_id: str, start_time: str, end_time: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.change_ops_window_request import (
                ChangeOpsWindowRequest,
            )
            from huaweicloudsdkrds.v3.model.ops_window_request import OpsWindowRequest

            body = OpsWindowRequest(start_time=start_time, end_time=end_time)
            request = ChangeOpsWindowRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.change_ops_window(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)
    async def list_instances_resource_metrics(self, *, engine: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_instances_resource_metrics_request import (
                ListInstancesResourceMetricsRequest,
            )

            request = ListInstancesResourceMetricsRequest(engine=engine)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.list_instances_resource_metrics(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class LogMixin:
    """P1-8: error/slow/audit logs."""

    _client: Any

    async def list_error_logs(
        self, *, instance_id: str, start_date: str, end_date: str,
        offset: int, limit: int,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_error_logs_request import (
                ListErrorLogsRequest,
            )

            request = ListErrorLogsRequest(
                instance_id=instance_id,
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=limit,
            )
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.list_error_logs(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc
            except Exception as exc:
                # The RDS log endpoints (/error-log, /slow-log) return a
                # different payload format than regular RDS APIs (XML or
                # text for PG) - the SDK model deserializer can throw
                # non-SdkException types here. Surface a clean envelope
                # instead of crashing the tool process.
                raise _log_response_error("list_error_logs", exc) from exc

        return await asyncio.to_thread(_call)

    async def list_slow_logs(
        self, *, instance_id: str, start_date: str, end_date: str,
        offset: int, limit: int,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_slow_logs_request import (
                ListSlowLogsRequest,
            )

            request = ListSlowLogsRequest(
                instance_id=instance_id,
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=limit,
            )
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.list_slow_logs(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc
            except Exception as exc:
                # Same non-standard payload as list_error_logs.
                raise _log_response_error("list_slow_logs", exc) from exc

        return await asyncio.to_thread(_call)

    async def download_errorlog(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.download_errorlog_request import (
                DownloadErrorlogRequest,
            )

            request = DownloadErrorlogRequest(instance_id=instance_id)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.download_errorlog(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def download_slowlog(
        self, *, instance_id: str, file_name: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.download_slowlog_request import (
                DownloadSlowlogRequest,
            )
            from huaweicloudsdkrds.v3.model.slowlog_download_request import (
                SlowlogDownloadRequest,
            )

            request = DownloadSlowlogRequest(
                instance_id=instance_id, body=SlowlogDownloadRequest(file_name=file_name)
            )
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.download_slowlog(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def set_auditlog_policy(
        self, *, instance_id: str, keep_days: int
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.set_auditlog_policy_request import (
                SetAuditlogPolicyRequest,
            )
            from huaweicloudsdkrds.v3.model.set_auditlog_policy_request_body import (
                SetAuditlogPolicyRequestBody,
            )

            body = SetAuditlogPolicyRequestBody(keep_days=str(keep_days))
            request = SetAuditlogPolicyRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.set_auditlog_policy(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def list_auditlogs(
        self, *, instance_id: str, limit: int
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_auditlogs_request import (
                ListAuditlogsRequest,
            )

            request = ListAuditlogsRequest(instance_id=instance_id, limit=str(limit))
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.list_auditlogs(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class ParamMixin:
    """P1-9: parameters and configuration templates."""

    _client: Any

    async def show_pg_parameters(
        self, *, instance_id: str, name: str | None
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.show_instance_configuration_request import (
                ShowInstanceConfigurationRequest,
            )

            request = ShowInstanceConfigurationRequest(instance_id=instance_id)
            try:
                data = cast(
                    dict[str, Any],
                    _to_dict(self._client.show_instance_configuration(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc
            params = data.get("configuration_parameters") or []
            if name:
                params = [p for p in params if p.get("name") == name]
            return {"configurations": params, "total_count": len(params)}

        return await asyncio.to_thread(_call)

    async def update_pg_parameter(
        self, *, instance_id: str, name: str, value: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            # The PG-specific path (v3/.../parameter/{name}) returns 403
            # DBS.280015 for credentials without its dedicated policy; the
            # generic instance-configuration API works and carries the
            # restart_required flag (live-verified).
            from huaweicloudsdkrds.v3.model.update_instance_configuration_request import (
                UpdateInstanceConfigurationRequest,
            )
            from huaweicloudsdkrds.v3.model.update_instance_configuration_request_body import (
                UpdateInstanceConfigurationRequestBody,
            )

            request = UpdateInstanceConfigurationRequest(
                instance_id=instance_id,
                body=UpdateInstanceConfigurationRequestBody(
                    values={name: value}
                ),
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.update_instance_configuration(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def list_configurations(self, *, engine: str | None) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_configurations_request import (
                ListConfigurationsRequest,
            )

            request = ListConfigurationsRequest()
            data = cast(dict[str, Any], _to_dict(self._client.list_configurations(request)))
            # engine filter is client-side for v3 API
            return data

        return await asyncio.to_thread(_call)

    async def apply_configuration(
        self, *, config_id: str, instance_ids: list[str]
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.apply_configuration_async_request import (
                ApplyConfigurationAsyncRequest,
            )
            from huaweicloudsdkrds.v3.model.apply_configuration_request import (
                ApplyConfigurationRequest,
            )

            body = ApplyConfigurationRequest(instance_ids=instance_ids)
            request = ApplyConfigurationAsyncRequest(config_id=config_id, body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.apply_configuration_async(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def compare_configurations(
        self, *, source_id: str, target_id: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.compare_configuration_request import (
                CompareConfigurationRequest,
            )
            from huaweicloudsdkrds.v3.model.compare_configuration_request_body import (
                CompareConfigurationRequestBody,
            )

            body = CompareConfigurationRequestBody(source_id=source_id, target_id=target_id)
            request = CompareConfigurationRequest(body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.compare_configuration(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class ExtensionMixin:
    """P1-10: PostgreSQL extensions."""

    _client: Any

    async def list_pg_extensions(
        self, *, instance_id: str, database_name: str, limit: int
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_postgresql_extension_request import (
                ListPostgresqlExtensionRequest,
            )

            request = ListPostgresqlExtensionRequest(
                instance_id=instance_id,
                database_name=database_name,
                limit=str(limit),
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.list_postgresql_extension(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_pg_extension(
        self, *, instance_id: str, database_name: str, extension_name: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_postgresql_extension_request import (
                CreatePostgresqlExtensionRequest,
            )
            from huaweicloudsdkrds.v3.model.extension_request import ExtensionRequest

            body = ExtensionRequest(
                database_name=database_name, extension_name=extension_name
            )
            request = CreatePostgresqlExtensionRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_postgresql_extension(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def delete_pg_extension(
        self, *, instance_id: str, database_name: str, extension_name: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.delete_postgresql_extension_request import (
                DeletePostgresqlExtensionRequest,
            )
            from huaweicloudsdkrds.v3.model.extension_request import ExtensionRequest

            body = ExtensionRequest(
                database_name=database_name, extension_name=extension_name
            )
            request = DeletePostgresqlExtensionRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.delete_postgresql_extension(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class CesClient:
    """Thin CES SDK wrapper (monitoring channel, v1 API)."""

    def __init__(self, settings: Any = None, sdk_client: Any = None) -> None:
        from huaweicloud_mcp_core.config import McpSettings
        from huaweicloud_mcp_core.credentials import CredentialScope, build_credentials

        self._settings = settings or McpSettings.from_env()
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from huaweicloudsdkces.v1 import CesClient as _SdkCesClient
            from huaweicloudsdkces.v1.region.ces_region import CesRegion

            self._client = (
                _SdkCesClient.new_builder()
                .with_credentials(build_credentials(CredentialScope.PROJECT, self._settings))
                .with_region(CesRegion.value_of(self._settings.region))
                .build()
            )

    async def show_metric_data(
        self,
        *,
        namespace: str,
        metric_name: str,
        dim_0: str,
        period: int,
        time_range: int,
        filt: str = "average",
    ) -> dict[str, Any]:
        # CES requires dimension format "dimension_name,resource_id"; for RDS
        # instances the dimension name is rds_cluster_id. A bare instance id
        # returns 400 ces.0013.
        if "," not in dim_0:
            dim_0 = f"rds_cluster_id,{dim_0}"
        def _call() -> dict[str, Any]:
            import time as _time

            from huaweicloudsdkces.v1.model.show_metric_data_request import (
                ShowMetricDataRequest,
            )

            now = int(_time.time() * 1000)
            request = ShowMetricDataRequest(
                namespace=namespace,
                metric_name=metric_name,
                dim_0=dim_0,
                filter=filt,
                period=str(period),
                _from=str(now - time_range * 1000),
                to=str(now),
            )
            try:
                return cast(dict[str, Any], _to_dict(self._client.show_metric_data(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_alarm(
        self, *, name: str, description: str | None, namespace: str,
        metric_name: str, dim_0: str, comparison_operator: str, value: float,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkces.v1.model.condition import Condition
            from huaweicloudsdkces.v1.model.create_alarm_metric import CreateAlarmMetric
            from huaweicloudsdkces.v1.model.create_alarm_request import CreateAlarmRequest
            from huaweicloudsdkces.v1.model.create_alarm_request_body import (
                CreateAlarmRequestBody,
            )
            from huaweicloudsdkces.v1.model.create_metric_dimension import (
                CreateMetricDimension,
            )

            metric = CreateAlarmMetric(
                namespace=namespace,
                metric_name=metric_name,
                dimensions=[CreateMetricDimension(name="instance_id", value=dim_0)],
            )
            body = CreateAlarmRequestBody(
                alarm_name=name,
                alarm_description=description,
                metric=metric,
                condition=Condition(
                    comparison_operator=comparison_operator,
                    count=1,
                    filter="average",
                    period=300,
                    unit="%",
                    value=float(value),
                ),
            )
            request = CreateAlarmRequest(body=body)
            try:
                return cast(dict[str, Any], _to_dict(self._client.create_alarm(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)
