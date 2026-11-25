# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Thin SDK wrapper for huaweicloudsdkrds. No business logic here."""

from __future__ import annotations

from typing import Any, cast

from huaweicloud_mcp_core.config import McpSettings
from huaweicloud_mcp_core.credentials import CredentialScope, build_credentials
from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException
from huaweicloudsdkrds.v3 import RdsClient as _SdkRdsClient
from huaweicloudsdkrds.v3.model.list_instances_request import ListInstancesRequest
from huaweicloudsdkrds.v3.model.list_job_info_request import ListJobInfoRequest
from huaweicloudsdkrds.v3.model.show_task_detail_request import ShowTaskDetailRequest

from mcp_server_rds_pg.client.backup_db_apis import BackupMixin, PgDatabaseMixin
from mcp_server_rds_pg.client.catalog_create import CatalogMixin, InstanceCreateMixin
from mcp_server_rds_pg.client.connection_apis import ConnectionMixin
from mcp_server_rds_pg.client.m3_apis import ExtensionMixin, LogMixin, ParamMixin, ResizeMixin
from mcp_server_rds_pg.client.network_apis import NetworkMixin
from mcp_server_rds_pg.client.throttle import guarded_call, reset_throttle  # noqa: F401

_SKIP_ATTRS = {
    "local_vars_configuration",
    "discriminator",
    "swagger_types",
    # SdkResponse transport-layer fields (see rfs_client.py for rationale):
    "_raw_content",
    "_status_code",
}


def sdk_to_dict(obj: Any) -> Any:
    """Recursively convert an SDK response object into plain JSON-compatible data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(key): sdk_to_dict(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sdk_to_dict(item) for item in obj]
    if not hasattr(obj, "__dict__"):
        return str(obj)
    result: dict[str, Any] = {}
    for key, value in vars(obj).items():
        if key in _SKIP_ATTRS or key.startswith("__") or callable(value):
            continue
        result[key.lstrip("_")] = sdk_to_dict(value)
    return result


def _is_not_found(exc: SdkException) -> bool:
    return getattr(exc, "status_code", None) == 404


class SdkRdsClient(
    CatalogMixin,
    InstanceCreateMixin,
    ConnectionMixin,
    BackupMixin,
    PgDatabaseMixin,
    ResizeMixin,
    LogMixin,
    ParamMixin,
    ExtensionMixin,
    NetworkMixin,
):
    """Async wrapper around the synchronous huaweicloudsdkrds v3 client."""

    def __init__(
        self,
        settings: McpSettings | None = None,
        sdk_client: Any = None,
    ) -> None:
        self._settings = settings or McpSettings.from_env()
        if sdk_client is not None:
            self._client = sdk_client
        else:
            self._client = (
                _SdkRdsClient.new_builder()
                .with_credentials(build_credentials(CredentialScope.PROJECT, self._settings))
                .with_region(_region_of(self._settings.region))
                .build()
            )

    async def list_instances(
        self,
        *,
        limit: int,
        offset: int | None = None,
        id: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            # Server-side filter: this service only manages PostgreSQL engines.
            # Exact-id lookups stay unfiltered so non-PG engines get the clear
            # engine-guard error instead of a misleading "not found".
            request = ListInstancesRequest(
                limit=limit,
                offset=offset,
                id=id,
                name=name,
                datastore_type="PostgreSQL" if id is None else None,
            )
            try:
                return cast(
                    dict[str, Any], sdk_to_dict(self._client.list_instances(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("list_instances", _call)

    async def list_job_info(self, *, job_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            request = ListJobInfoRequest(id=job_id)
            try:
                response = self._client.list_job_info(request)
            except SdkException as exc:
                if getattr(exc, "error_code", None) in ("DBS.200543",):
                    return {}
                raise wrap_sdk_error(exc) from exc
            return cast(dict[str, Any], sdk_to_dict(response))

        return await guarded_call("list_job_info", _call)

    async def show_task_detail(self, *, job_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            request = ShowTaskDetailRequest(id=job_id)
            try:
                response = self._client.show_task_detail(request)
            except SdkException as exc:
                if _is_not_found(exc):
                    return {}
                raise wrap_sdk_error(exc) from exc
            return cast(dict[str, Any], sdk_to_dict(response))

        return await guarded_call("show_task_detail", _call)


    async def reboot_instance(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.instance_restart_requset_body import (
                InstanceRestartRequsetBody,
            )
            from huaweicloudsdkrds.v3.model.restart_configuration import (
                RestartConfiguration,
            )
            from huaweicloudsdkrds.v3.model.start_instance_restart_action_request import (
                StartInstanceRestartActionRequest,
            )

            # restart=RestartConfiguration() is required - an empty body
            # yields DBS.280001 Parameter error.
            request = StartInstanceRestartActionRequest(
                instance_id=instance_id,
                body=InstanceRestartRequsetBody(restart=RestartConfiguration()),
            )
            try:
                return cast(
                    dict[str, Any],
                    sdk_to_dict(self._client.start_instance_restart_action(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("reboot_instance", _call)

    async def stop_instance(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.stop_instance_request import (
                StopInstanceRequest,
            )

            request = StopInstanceRequest(instance_id=instance_id)
            try:
                return cast(dict[str, Any], sdk_to_dict(self._client.stop_instance(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("stop_instance", _call)

    async def start_instance(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.startup_instance_request import (
                StartupInstanceRequest,
            )

            request = StartupInstanceRequest(instance_id=instance_id)
            try:
                return cast(dict[str, Any], sdk_to_dict(self._client.startup_instance(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("start_instance", _call)


def _region_of(region: str) -> Any:
    from huaweicloudsdkrds.v3.region.rds_region import RdsRegion

    return RdsRegion.value_of(region)
