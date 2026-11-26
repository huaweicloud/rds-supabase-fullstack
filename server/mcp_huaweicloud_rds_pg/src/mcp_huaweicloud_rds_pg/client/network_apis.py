# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M4 client APIs: network environment + EIP.

Channels (SDK facts verified against 3.1.223):
- VPC v2:  ListVpcs / CreateVpc / ListSubnets / CreateSubnet (ordinary subnets
  live in v2 - v3 only serves clouddcn subnets).
- VPC v3:  ListSecurityGroups / CreateSecurityGroup / CreateSecurityGroupRule /
  ListSecurityGroupRules.
- EIP v2:  CreatePublicip / DeletePublicip / ShowPublicip / ListPublicips /
  BatchCreatePublicipTags (the VPC SDK ships no publicip models, so the EIP
  package carries EIP body create/delete).
- EPS v1:  ListEnterpriseProject / CreateEnterpriseProject (global service,
  pinned to cn-north-4 - narrow region list, mgr instance_catalog.py parity).

Lazy SDK imports inside each _call so the module imports without the SDKs
installed (service/tools tests inject fakes).
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException

# EPS is a global service whose region list is narrow; pin it like the mgr
# repo does (instance_catalog.py EPS_REGION).
EPS_REGION = "cn-north-4"


def _to_dict(obj: Any) -> Any:
    from mcp_huaweicloud_rds_pg.client.sdk_rds import sdk_to_dict

    return sdk_to_dict(obj)


class VpcChannel:
    """VPC v2 + v3 SDK wrapper (network discovery and creation channel)."""

    def __init__(self, settings: Any = None, sdk_client: Any = None) -> None:
        from huaweicloud_mcp_core.config import McpSettings

        self._settings = settings or McpSettings.from_env()
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from huaweicloudsdkvpc.v2 import VpcClient as _SdkVpcClient
            from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

            self._client = (
                _SdkVpcClient.new_builder()
                .with_credentials(_project_credentials(self._settings))
                .with_region(VpcRegion.value_of(self._settings.region))
                .build()
            )

    async def list_vpcs(self, *, limit: int = 100) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v2.model.list_vpcs_request import ListVpcsRequest

            request = ListVpcsRequest(limit=limit)
            try:
                return cast(dict[str, Any], _to_dict(self._client.list_vpcs(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_vpc(self, *, name: str, cidr: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v2.model.create_vpc_option import CreateVpcOption
            from huaweicloudsdkvpc.v2.model.create_vpc_request import CreateVpcRequest
            from huaweicloudsdkvpc.v2.model.create_vpc_request_body import (
                CreateVpcRequestBody,
            )

            body = CreateVpcRequestBody(vpc=CreateVpcOption(name=name, cidr=cidr))
            request = CreateVpcRequest(body=body)
            try:
                return cast(dict[str, Any], _to_dict(self._client.create_vpc(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def list_subnets(self, *, vpc_id: str, limit: int = 100) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v2.model.list_subnets_request import (
                ListSubnetsRequest,
            )

            request = ListSubnetsRequest(vpc_id=vpc_id, limit=limit)
            try:
                return cast(dict[str, Any], _to_dict(self._client.list_subnets(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_subnet(
        self, *, vpc_id: str, name: str, cidr: str, availability_zone: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            import ipaddress

            from huaweicloudsdkvpc.v2.model.create_subnet_option import (
                CreateSubnetOption,
            )
            from huaweicloudsdkvpc.v2.model.create_subnet_request import (
                CreateSubnetRequest,
            )
            from huaweicloudsdkvpc.v2.model.create_subnet_request_body import (
                CreateSubnetRequestBody,
            )

            # VPC.0201 without gateway_ip: the API requires an explicit
            # gateway; derive the first host of the subnet CIDR (SDK fact
            # verified live, cn-north-4, 2026-11).
            gateway_ip = str(next(ipaddress.ip_network(cidr, strict=False).hosts()))
            body = CreateSubnetRequestBody(
                subnet=CreateSubnetOption(
                    vpc_id=vpc_id, name=name, cidr=cidr,
                    availability_zone=availability_zone,
                    gateway_ip=gateway_ip,
                )
            )
            request = CreateSubnetRequest(body=body)
            try:
                return cast(dict[str, Any], _to_dict(self._client.create_subnet(request)))
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    # -- security groups: VPC v3 -------------------------------------------

    async def list_security_groups(self, *, limit: int = 100) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v3.model.list_security_groups_request import (
                ListSecurityGroupsRequest,
            )

            request = ListSecurityGroupsRequest(limit=limit)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.list_security_groups(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def list_security_group_rules(
        self, *, security_group_id: str, limit: int = 200
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v3.model.list_security_group_rules_request import (
                ListSecurityGroupRulesRequest,
            )

            request = ListSecurityGroupRulesRequest(
                security_group_id=security_group_id, limit=limit
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.list_security_group_rules(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_security_group(self, *, name: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v3.model.create_security_group_option import (
                CreateSecurityGroupOption,
            )
            from huaweicloudsdkvpc.v3.model.create_security_group_request import (
                CreateSecurityGroupRequest,
            )
            from huaweicloudsdkvpc.v3.model.create_security_group_request_body import (
                CreateSecurityGroupRequestBody,
            )

            body = CreateSecurityGroupRequestBody(
                security_group=CreateSecurityGroupOption(
                    name=name, description="created by rds-pg mcp"
                )
            )
            request = CreateSecurityGroupRequest(body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.create_security_group(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_security_group_rule(
        self,
        *,
        security_group_id: str,
        direction: str,
        protocol: str,
        multiport: str,
        remote_ip_prefix: str,
        description: str = "",
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkvpc.v3.model.create_security_group_rule_option import (
                CreateSecurityGroupRuleOption,
            )
            from huaweicloudsdkvpc.v3.model.create_security_group_rule_request import (
                CreateSecurityGroupRuleRequest,
            )
            from huaweicloudsdkvpc.v3.model.create_security_group_rule_request_body import (
                CreateSecurityGroupRuleRequestBody,
            )

            option = CreateSecurityGroupRuleOption(
                security_group_id=security_group_id,
                direction=direction,
                ethertype="IPv4",
                protocol=protocol,
                multiport=multiport,
                remote_ip_prefix=remote_ip_prefix,
                description=description,
            )
            body = CreateSecurityGroupRuleRequestBody(security_group_rule=option)
            request = CreateSecurityGroupRuleRequest(body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_security_group_rule(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class EipChannel:
    """EIP v2 SDK wrapper (public IP body lifecycle channel)."""

    def __init__(self, settings: Any = None, sdk_client: Any = None) -> None:
        from huaweicloud_mcp_core.config import McpSettings

        self._settings = settings or McpSettings.from_env()
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from huaweicloudsdkeip.v2 import EipClient as _SdkEipClient
            from huaweicloudsdkeip.v2.region.eip_region import EipRegion

            self._client = (
                _SdkEipClient.new_builder()
                .with_credentials(_project_credentials(self._settings))
                .with_region(EipRegion.value_of(self._settings.region))
                .build()
            )

    async def create_publicip(
        self,
        *,
        alias: str,
        charge_mode: str,
        bandwidth_size: int,
        bandwidth_name: str,
    ) -> dict[str, Any]:
        """Create an EIP with a PER (dedicated) bandwidth, post-paid only.

        charge_mode: 'traffic' (pay-per-GB) or 'bandwidth' (pay-per-Mbps).
        """

        def _call() -> dict[str, Any]:
            from huaweicloudsdkeip.v2.model.create_publicip_bandwidth_option import (
                CreatePublicipBandwidthOption,
            )
            from huaweicloudsdkeip.v2.model.create_publicip_option import (
                CreatePublicipOption,
            )
            from huaweicloudsdkeip.v2.model.create_publicip_request import (
                CreatePublicipRequest,
            )
            from huaweicloudsdkeip.v2.model.create_publicip_request_body import (
                CreatePublicipRequestBody,
            )

            body = CreatePublicipRequestBody(
                publicip=CreatePublicipOption(type="5_bgp", alias=alias),
                bandwidth=CreatePublicipBandwidthOption(
                    name=bandwidth_name,
                    share_type="PER",
                    size=bandwidth_size,
                    charge_mode=charge_mode,
                ),
            )
            request = CreatePublicipRequest(body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.create_publicip(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def show_publicip(self, *, publicip_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkeip.v2.model.show_publicip_request import (
                ShowPublicipRequest,
            )

            request = ShowPublicipRequest(publicip_id=publicip_id)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.show_publicip(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def list_publicips(self, *, limit: int = 200) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkeip.v2.model.list_publicips_request import (
                ListPublicipsRequest,
            )

            request = ListPublicipsRequest(limit=limit)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.list_publicips(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def delete_publicip(self, *, publicip_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkeip.v2.model.delete_publicip_request import (
                DeletePublicipRequest,
            )

            request = DeletePublicipRequest(publicip_id=publicip_id)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.delete_publicip(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def tag_publicip(self, *, publicip_id: str, key: str, value: str) -> None:
        def _call() -> None:
            from huaweicloudsdkeip.v2.model.batch_create_publicip_tags_request import (
                BatchCreatePublicipTagsRequest,
            )
            from huaweicloudsdkeip.v2.model.batch_create_publicip_tags_request_body import (
                BatchCreatePublicipTagsRequestBody,
            )
            from huaweicloudsdkeip.v2.model.resource_tag_option import ResourceTagOption

            body = BatchCreatePublicipTagsRequestBody(
                action="create", tags=[ResourceTagOption(key=key, value=value)]
            )
            request = BatchCreatePublicipTagsRequest(publicip_id=publicip_id, body=body)
            try:
                self._client.batch_create_publicip_tags(request)
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        await asyncio.to_thread(_call)


class EpsChannel:
    """EPS v1 SDK wrapper (global service, pinned to cn-north-4)."""

    def __init__(self, settings: Any = None, sdk_client: Any = None) -> None:
        from huaweicloud_mcp_core.config import McpSettings

        self._settings = settings or McpSettings.from_env()
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from huaweicloudsdkeps.v1 import EpsClient as _SdkEpsClient
            from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

            self._client = (
                _SdkEpsClient.new_builder()
                .with_credentials(_global_credentials(self._settings))
                .with_region(EpsRegion.value_of(EPS_REGION))
                .build()
            )

    async def list_enterprise_projects(self, *, limit: int = 100) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkeps.v1.model.list_enterprise_project_request import (
                ListEnterpriseProjectRequest,
            )

            request = ListEnterpriseProjectRequest(limit=limit)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.list_enterprise_project(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    async def create_enterprise_project(
        self, *, name: str, description: str | None = None
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkeps.v1.model.create_enterprise_project_request import (
                CreateEnterpriseProjectRequest,
            )
            from huaweicloudsdkeps.v1.model.enterprise_project import (
                EnterpriseProject,
            )

            body = EnterpriseProject(name=name, description=description)
            request = CreateEnterpriseProjectRequest(body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_enterprise_project(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


class NetworkMixin:
    # module-level guard helper lives in NetworkMixin so every write tool
    # path can share it

    async def list_ai_applications(self, *, limit: int = 100) -> dict[str, Any]:
        """RDS AI applications (Supabase/GraphRAG/ContextBase/...) with their
        bound managed instances - the generic detection channel for the
        AI-application guard."""

        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_ai_applications_request import (
                ListAiApplicationsRequest,
            )

            request = ListAiApplicationsRequest(limit=str(limit))
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.list_ai_applications(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)

    """RDS-side network APIs: EIP bind/unbind (AttachEip PUT public-ip)."""

    _client: Any

    async def attach_eip(
        self,
        *,
        instance_id: str,
        public_ip: str | None,
        public_ip_id: str | None,
        is_bind: bool,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.attach_eip_request import AttachEipRequest
            from huaweicloudsdkrds.v3.model.bind_eip_request import BindEipRequest

            body = BindEipRequest(
                public_ip=public_ip, public_ip_id=public_ip_id, is_bind=is_bind
            )
            request = AttachEipRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.attach_eip(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await asyncio.to_thread(_call)


def _project_credentials(settings: Any) -> Any:
    from huaweicloud_mcp_core.credentials import CredentialScope, build_credentials

    return build_credentials(CredentialScope.PROJECT, settings)


def _global_credentials(settings: Any) -> Any:
    from huaweicloud_mcp_core.credentials import CredentialScope, build_credentials

    return build_credentials(CredentialScope.GLOBAL, settings)


__all__ = [
    "EPS_REGION",
    "EipChannel",
    "EpsChannel",
    "NetworkMixin",
    "VpcChannel",
]
