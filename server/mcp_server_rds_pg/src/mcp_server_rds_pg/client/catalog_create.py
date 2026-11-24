# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 client additions: catalog, instance creation, admin password reset.

Lazy SDK imports inside each _call so the module imports without the SDK
installed (service/tools tests inject fakes).
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException


class CatalogMixin:
    """Read-only catalog endpoints feeding creation planning."""

    _client: Any

    async def list_flavors(
        self, *, version: str, availability_zone: str | None = None
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_flavors_request import ListFlavorsRequest

            request = ListFlavorsRequest(
                database_name="PostgreSQL", version_name=version,
            )
            return cast(dict[str, Any], _to_dict(self._client.list_flavors(request)))

        return await asyncio.to_thread(_call)

    async def list_datastores(self, *, version: str | None = None) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_datastores_request import (
                ListDatastoresRequest,
            )

            request = ListDatastoresRequest(database_name="PostgreSQL")
            return cast(dict[str, Any], _to_dict(self._client.list_datastores(request)))

        return await asyncio.to_thread(_call)

    async def list_storage_types(self, *, version: str, ha_mode: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_storage_types_request import (
                ListStorageTypesRequest,
            )

            request = ListStorageTypesRequest(
                database_name="PostgreSQL", version_name=version, ha_mode=ha_mode,
            )
            return cast(dict[str, Any], _to_dict(self._client.list_storage_types(request)))

        return await asyncio.to_thread(_call)

    async def show_quotas(self) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.show_quotas_request import ShowQuotasRequest

            return cast(dict[str, Any], _to_dict(self._client.show_quotas(ShowQuotasRequest())))

        return await asyncio.to_thread(_call)


class InstanceCreateMixin:
    """Instance creation and admin password reset."""

    _client: Any

    async def create_instance(self, *, body: dict[str, Any]) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_instance_request import (
                CreateInstanceRequest,
            )
            from huaweicloudsdkrds.v3.model.instance_request import InstanceRequest

            model = InstanceRequest()
            for key, value in body.items():
                if value is not None:
                    setattr(model, key, _deserialize_nested(key, value))
            request = CreateInstanceRequest(body=model)
            return cast(
                dict[str, Any], _to_dict(self._client.create_instance(request))
            )

        return await asyncio.to_thread(_call)

    async def reset_admin_password(
        self, *, instance_id: str, password: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.pwd_reset_request import PwdResetRequest
            from huaweicloudsdkrds.v3.model.reset_pwd_request import ResetPwdRequest

            body = PwdResetRequest(password=password)
            request = ResetPwdRequest(instance_id=instance_id, body=body)
            return cast(dict[str, Any], _to_dict(self._client.reset_pwd(request)))

        return await asyncio.to_thread(_call)


def _to_dict(obj: Any) -> Any:
    from mcp_server_rds_pg.client.sdk_rds import sdk_to_dict

    return sdk_to_dict(obj)


_NESTED_MODELS = {
    "datastore": "Datastore",
    "volume": "Volume",
    "ha": "Ha",
    "charge_info": "ChargeInfo",
    "backup_strategy": "BackupStrategy",
}


def _deserialize_nested(key: str, value: dict[str, Any]) -> Any:
    """Convert plain dict body fields into their SDK model counterparts."""
    module = "huaweicloudsdkrds.v3.model"
    name = _NESTED_MODELS.get(key)
    if not name:
        return value
    import importlib

    cls = getattr(importlib.import_module(f"{module}.{_snake(name)}"), name)
    return cls(**value)


def _snake(name: str) -> str:
    lowered = name[0].lower()
    for ch in name[1:]:
        lowered += ("_" + ch.lower()) if ch.isupper() else ch
    return lowered


__all__ = ["CatalogMixin", "InstanceCreateMixin", "SdkException", "wrap_sdk_error"]
