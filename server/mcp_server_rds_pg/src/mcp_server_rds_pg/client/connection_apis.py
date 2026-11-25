# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""P0-2 client APIs: SSL cert link, port, security group, pg_hba, DNS name."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException


class ConnectionMixin:
    _client: Any

    async def list_ssl_cert_download_link(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_ssl_cert_download_link_request import (
                ListSslCertDownloadLinkRequest,
            )

            request = ListSslCertDownloadLinkRequest(instance_id=instance_id)
            return cast(
                dict[str, Any], _to_dict(self._client.list_ssl_cert_download_link(request))
            )

        return await asyncio.to_thread(_call)

    async def update_port(self, *, instance_id: str, port: int) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.update_db_port_request import (
                UpdateDbPortRequest,
            )
            from huaweicloudsdkrds.v3.model.update_port_request import UpdatePortRequest

            body = UpdateDbPortRequest(port=str(port))
            request = UpdatePortRequest(instance_id=instance_id, body=body)
            return cast(dict[str, Any], _to_dict(self._client.update_port(request)))

        return await asyncio.to_thread(_call)

    async def set_security_group(
        self, *, instance_id: str, security_group_id: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.security_group_request import (
                SecurityGroupRequest,
            )
            from huaweicloudsdkrds.v3.model.set_security_group_request import (
                SetSecurityGroupRequest,
            )

            body = SecurityGroupRequest(security_group_id=security_group_id)
            request = SetSecurityGroupRequest(instance_id=instance_id, body=body)
            return cast(
                dict[str, Any], _to_dict(self._client.set_security_group(request))
            )

        return await asyncio.to_thread(_call)

    async def list_postgresql_hba_info(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_postgresql_hba_info_request import (
                ListPostgresqlHbaInfoRequest,
            )

            request = ListPostgresqlHbaInfoRequest(instance_id=instance_id)
            return cast(
                dict[str, Any],
                _to_dict(self._client.list_postgresql_hba_info(request)),
            )

        return await asyncio.to_thread(_call)

    async def add_postgresql_hba_conf(
        self, *, instance_id: str, entries: list[dict[str, Any]]
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.add_postgresql_hba_conf_request import (
                AddPostgresqlHbaConfRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_hba_conf import (
                PostgresqlHbaConf,
            )

            models = [PostgresqlHbaConf(**entry) for entry in entries]
            request = AddPostgresqlHbaConfRequest(
                instance_id=instance_id, body=models
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.add_postgresql_hba_conf(request)),
            )

        return await asyncio.to_thread(_call)

    # -- intranet DNS name (M4b; user guide §4.7.2) --------------------------

    async def create_dns_name(
        self, *, instance_id: str, dns_type: str = "private"
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_dns_name_request import (
                CreateDnsNameRequest,
            )
            from huaweicloudsdkrds.v3.model.create_dns_name_request_body import (
                CreateDnsNameRequestBody,
            )

            body = CreateDnsNameRequestBody(dns_type=dns_type)
            request = CreateDnsNameRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.create_dns_name(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def update_dns_name(
        self, *, instance_id: str, dns_name: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.modify_dns_name_request_body import (
                ModifyDnsNameRequestBody,
            )
            from huaweicloudsdkrds.v3.model.update_dns_name_request import (
                UpdateDnsNameRequest,
            )

            body = ModifyDnsNameRequestBody(dns_name=dns_name)
            request = UpdateDnsNameRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.update_dns_name(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def show_dns_name(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.show_dns_name_request import (
                ShowDnsNameRequest,
            )

            request = ShowDnsNameRequest(instance_id=instance_id)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.show_dns_name(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


def _to_dict(obj: Any) -> Any:
    from mcp_server_rds_pg.client.sdk_rds import sdk_to_dict

    return sdk_to_dict(obj)
