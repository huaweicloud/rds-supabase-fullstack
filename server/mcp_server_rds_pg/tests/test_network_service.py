# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Tests for the M4 network service: discovery, creation, EIP lifecycle."""

from __future__ import annotations

from typing import Any

import pytest
from huaweicloud_mcp_core.errors import McpToolError

from conftest import FakeSdkRdsClient
from mcp_server_rds_pg.service.network_service import NetworkService
from mcp_server_rds_pg.service.plans import PlanStore

DEFAULT_VPC_ID = "11111111-2222-3333-4444-555555555555"
DEFAULT_SUBNET_ID = "66666666-7777-8888-9999-000000000000"
DEFAULT_SG_ID = "5f4251d3-6c16-4345-b2bb-8947dc7e4d72"


class FakeVpcChannel:
    def __init__(self) -> None:
        self.vpcs: list[dict[str, Any]] = [
            {"id": DEFAULT_VPC_ID, "name": "default", "cidr": "192.168.0.0/16",
             "status": "OK"},
            {"id": "vpc-2", "name": "other", "cidr": "10.0.0.0/8", "status": "OK"},
        ]
        self.subnets: dict[str, list[dict[str, Any]]] = {
            DEFAULT_VPC_ID: [
                {"id": DEFAULT_SUBNET_ID, "name": "default",
                 "vpc_id": DEFAULT_VPC_ID, "cidr": "192.168.0.0/24",
                 "availability_zone": "cn-north-4a", "gateway_ip": "192.168.0.1",
                 "available_ip_address_count": 251},
            ],
            "vpc-2": [
                {"id": "subnet-2", "name": "s2", "vpc_id": "vpc-2",
                 "cidr": "10.0.1.0/24", "availability_zone": "cn-north-4b",
                 "gateway_ip": "10.0.1.1", "available_ip_address_count": 251},
            ],
        }
        self.security_groups: list[dict[str, Any]] = [
            {"id": DEFAULT_SG_ID, "name": "default", "description": "x"},
            {"id": "sg-open", "name": "pg-open", "description": "y"},
            {"id": "sg-ssh", "name": "ssh-only", "description": "z"},
        ]
        self.rules: dict[str, list[dict[str, Any]]] = {
            DEFAULT_SG_ID: [
                {"id": "r1", "direction": "ingress", "protocol": "tcp",
                 "multiport": "22", "action": "allow",
                 "remote_ip_prefix": "0.0.0.0/0"},
            ],
            "sg-open": [
                {"id": "r2", "direction": "ingress", "protocol": "tcp",
                 "multiport": "5432", "action": "allow",
                 "remote_ip_prefix": "10.0.0.0/24"},
            ],
            "sg-ssh": [
                {"id": "r3", "direction": "egress", "protocol": "tcp",
                 "multiport": "5432", "action": "allow",
                 "remote_ip_prefix": "0.0.0.0/0"},
            ],
        }
        self.created_vpcs: list[dict[str, Any]] = []
        self.created_subnets: list[dict[str, Any]] = []
        self.created_sgs: list[dict[str, Any]] = []
        self.created_rules: list[dict[str, Any]] = []

    async def list_vpcs(self, *, limit: int = 100) -> dict[str, Any]:
        return {"vpcs": self.vpcs[:limit]}

    async def create_vpc(self, *, name: str, cidr: str) -> dict[str, Any]:
        created = {"id": "vpc-new", "name": name, "cidr": cidr, "status": "OK"}
        self.created_vpcs.append({"name": name, "cidr": cidr})
        return {"vpc": created}

    async def list_subnets(self, *, vpc_id: str, limit: int = 100) -> dict[str, Any]:
        return {"subnets": self.subnets.get(vpc_id, [])[:limit]}

    async def create_subnet(
        self, *, vpc_id: str, name: str, cidr: str, availability_zone: str
    ) -> dict[str, Any]:
        self.created_subnets.append(
            {"vpc_id": vpc_id, "name": name, "cidr": cidr, "az": availability_zone}
        )
        return {"subnet": {"id": "subnet-new", "name": name, "cidr": cidr,
                           "vpc_id": vpc_id, "availability_zone": availability_zone}}

    async def list_security_groups(self, *, limit: int = 100) -> dict[str, Any]:
        return {"security_groups": self.security_groups[:limit]}

    async def list_security_group_rules(
        self, *, security_group_id: str, limit: int = 200
    ) -> dict[str, Any]:
        return {"security_group_rules": self.rules.get(security_group_id, [])}

    async def create_security_group(self, *, name: str) -> dict[str, Any]:
        self.created_sgs.append({"name": name})
        group_id = f"sg-new-{len(self.created_sgs)}"
        self.security_groups.append({"id": group_id, "name": name, "description": ""})
        self.rules[group_id] = []
        return {"security_group": {"id": group_id, "name": name}}

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
        self.created_rules.append(
            {
                "security_group_id": security_group_id,
                "direction": direction,
                "protocol": protocol,
                "multiport": multiport,
                "remote_ip_prefix": remote_ip_prefix,
            }
        )
        return {"security_group_rule": {"id": "rule-new",
                                        "remote_ip_prefix": remote_ip_prefix}}


class FakeEipChannel:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.tags: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self.publicips: dict[str, dict[str, Any]] = {
            "eip-1": {"id": "eip-1", "public_ip_address": "1.2.3.4",
                      "status": "UNBOUND"},
        }

    async def create_publicip(
        self, *, alias: str, charge_mode: str, bandwidth_size: int,
        bandwidth_name: str,
    ) -> dict[str, Any]:
        self.created.append({"alias": alias, "charge_mode": charge_mode,
                             "bandwidth_size": bandwidth_size})
        eip_id = f"eip-new-{len(self.created)}"
        self.publicips[eip_id] = {
            "id": eip_id, "public_ip_address": "5.6.7.8", "status": "UNBOUND",
            "type": "5_bgp",
        }
        return {"publicip": self.publicips[eip_id]}

    async def show_publicip(self, *, publicip_id: str) -> dict[str, Any]:
        return {"publicip": self.publicips.get(publicip_id, {})}

    async def list_publicips(self, *, limit: int = 200) -> dict[str, Any]:
        return {"publicips": list(self.publicips.values())}

    async def delete_publicip(self, *, publicip_id: str) -> dict[str, Any]:
        self.deleted.append(publicip_id)
        return {}

    async def tag_publicip(self, *, publicip_id: str, key: str, value: str) -> None:
        self.tags.append({"publicip_id": publicip_id, "key": key, "value": value})


class FakeEpsChannel:
    def __init__(self, *, fail: bool = False, projects: list[dict[str, Any]] | None = None):
        self.fail = fail
        self.projects = projects if projects is not None else [
            {"id": "0", "name": "default", "status": 1},
            {"id": "1", "name": "proj-1", "status": 1},
        ]
        self.created: list[dict[str, Any]] = []

    async def list_enterprise_projects(self, *, limit: int = 100) -> dict[str, Any]:
        if self.fail:
            raise McpToolError("MCP_SDK_ERROR", "eps unavailable")
        return {"enterprise_projects": self.projects}

    async def create_enterprise_project(
        self, *, name: str, description: str | None = None
    ) -> dict[str, Any]:
        self.created.append({"name": name, "description": description})
        return {"enterprise_project": {"id": "ep-new", "name": name}}


@pytest.fixture
def network(
    plans: PlanStore,
    fake_client: FakeSdkRdsClient,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[NetworkService, FakeVpcChannel, FakeEipChannel, FakeEpsChannel]:
    monkeypatch.setenv("RDS_PG_ENABLE_WRITES", "true")
    vpc, eip, eps = FakeVpcChannel(), FakeEipChannel(), FakeEpsChannel()
    service = NetworkService(
        client=fake_client, plans=plans, vpc=vpc, eip=eip, eps=eps  # type: ignore[arg-type]
    )
    return service, vpc, eip, eps  # type: ignore[return-value]


# -- discovery ------------------------------------------------------------


async def test_discover_aggregates_and_recommends_default(network) -> None:
    service, _, _, _ = network
    result = await service.discover()
    placement = result["placement_recommendation"]
    assert placement["recommended_vpc"]["id"] == DEFAULT_VPC_ID
    assert placement["recommended_subnet"]["id"] == DEFAULT_SUBNET_ID
    groups = result["security_groups"]
    by_name = {g["name"]: g for g in groups}
    assert by_name["pg-open"]["open_5432"] is True
    assert by_name["default"]["open_5432"] is False
    # egress rule must not count as 5432-open
    assert by_name["ssh-only"]["open_5432"] is False
    sg_plan = result["security_group_plan"]
    assert sg_plan["candidates_with_5432"] == ["sg-open"]
    assert result["enterprise_projects"][0]["name"] == "default"


async def test_discover_degrades_eps_failure(network) -> None:
    _service, vpc, eip, _ = network
    failing = NetworkService(
        client=FakeSdkRdsClient(), plans=PlanStore(path="/tmp/plans-t1.sqlite3"),
        vpc=vpc, eip=eip, eps=FakeEpsChannel(fail=True),  # type: ignore[arg-type]
    )
    result = await failing.discover()
    assert result["enterprise_projects"] is None
    assert result["vpcs"]  # rest of discovery still returned


async def test_list_subnets_requires_known_vpc(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.list_subnets(vpc_id="vpc-nope")
    assert exc_info.value.code == "MCP_NOT_FOUND"


# -- creation: VPC --------------------------------------------------------


async def test_create_vpc_two_stage(network) -> None:
    service, vpc, _, _ = network
    preview = await service.create_vpc(name="e2e-vpc", cidr="172.16.0.0/16")
    assert preview["status"] == "confirmation_required"
    assert preview["changes"] == {"name": "e2e-vpc", "cidr": "172.16.0.0/16"}
    assert not vpc.created_vpcs
    result = await service.create_vpc(
        name="e2e-vpc", cidr="172.16.0.0/16",
        confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert vpc.created_vpcs == [{"name": "e2e-vpc", "cidr": "172.16.0.0/16"}]


async def test_create_vpc_rejects_public_cidr(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.create_vpc(name="bad", cidr="8.8.8.0/24")
    assert exc_info.value.code == "MCP_INVALID_ARGS"
    with pytest.raises(McpToolError):
        await service.create_vpc(name="bad", cidr="not-a-cidr")


# -- creation: subnet -----------------------------------------------------


async def test_create_subnet_rejects_cidr_outside_vpc(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.create_subnet(
            vpc_id=DEFAULT_VPC_ID, name="s", cidr="10.99.0.0/24",
            availability_zone="cn-north-4a",
        )
    assert exc_info.value.code == "MCP_INVALID_ARGS"


async def test_create_subnet_two_stage(network) -> None:
    service, vpc, _, _ = network
    preview = await service.create_subnet(
        vpc_id=DEFAULT_VPC_ID, name="e2e-subnet", cidr="192.168.5.0/24",
        availability_zone="cn-north-4a",
    )
    assert preview["status"] == "confirmation_required"
    result = await service.create_subnet(
        vpc_id=DEFAULT_VPC_ID, name="e2e-subnet", cidr="192.168.5.0/24",
        availability_zone="cn-north-4a",
        confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert vpc.created_subnets[0]["cidr"] == "192.168.5.0/24"


# -- creation: security group (three-choice source) ------------------------


async def test_create_sg_custom_bounded_cidr(network) -> None:
    service, vpc, _, _ = network
    preview = await service.create_security_group(
        name="e2e-sg", open_5432_from="10.0.0.0/24"
    )
    assert preview["changes"]["resolved_source_cidr"] == "10.0.0.0/24"
    result = await service.create_security_group(
        name="e2e-sg", open_5432_from="10.0.0.0/24",
        confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert vpc.created_rules[0]["remote_ip_prefix"] == "10.0.0.0/24"
    assert vpc.created_rules[0]["multiport"] == "5432"


async def test_create_sg_bare_ip_becomes_32(network) -> None:
    service, _, _, _ = network
    preview = await service.create_security_group(
        name="sg-ip", open_5432_from="1.2.3.4"
    )
    assert preview["changes"]["resolved_source_cidr"] == "1.2.3.4/32"


async def test_create_sg_open_requires_explicit_keyword(network) -> None:
    service, _, _, _ = network
    preview = await service.create_security_group(
        name="sg-open", open_5432_from="open"
    )
    assert preview["changes"]["resolved_source_cidr"] == "0.0.0.0/0"
    assert any("internet" in w for w in preview["warnings"])
    # bare 0.0.0.0/0 without the 'open' keyword is rejected
    with pytest.raises(McpToolError):
        await service.create_security_group(
            name="sg-open", open_5432_from="0.0.0.0/0"
        )


async def test_create_sg_default_source_is_subnet_cidr(network) -> None:
    service, _, _, _ = network
    preview = await service.create_security_group(
        name="sg-sub", subnet_id=DEFAULT_SUBNET_ID
    )
    assert preview["changes"]["resolved_source_cidr"] == "192.168.0.0/24"


async def test_create_sg_missing_source_rejected(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.create_security_group(name="sg-x")
    assert exc_info.value.code == "MCP_INVALID_ARGS"


async def test_create_sg_empty_group_no_rule(network) -> None:
    service, vpc, _, _ = network
    preview = await service.create_security_group(name="sg-empty", open_5432=False)
    assert preview["changes"] == {"name": "sg-empty", "open_5432": False}
    result = await service.create_security_group(
        name="sg-empty", open_5432=False, confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert vpc.created_rules == []


# -- creation: EIP ---------------------------------------------------------


async def test_create_eip_rejects_missing_billing_decision(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.create_eip(name="e", billing_type="prePaid")
    assert "user-only" in exc_info.value.message


async def test_create_eip_two_stage_with_usage_tag(network) -> None:
    service, _, eip, _ = network
    preview = await service.create_eip(
        name="e2e-eip", billing_type="traffic", bandwidth_size=5
    )
    assert preview["status"] == "confirmation_required"
    assert not eip.created
    result = await service.create_eip(
        name="e2e-eip", billing_type="traffic", bandwidth_size=5,
        confirm=True, plan_id=preview["plan_id"],
    )
    assert result["status"] == "submitted"
    assert eip.created[0]["charge_mode"] == "traffic"
    assert eip.tags == [{"publicip_id": "eip-new-1", "key": "USAGE_FOR",
                         "value": "rds-pg"}]


# -- EIP bind/unbind -------------------------------------------------------


async def test_bind_eip_requires_active_instance(
    network, fake_client: FakeSdkRdsClient
) -> None:
    service, _, _, _ = network
    fake_client.instances["inst-1"]["status"] = "REBOOTING"
    preview = await service.bind_eip(instance_id="inst-1", public_ip_id="eip-1")
    with pytest.raises(McpToolError) as exc_info:
        await service.bind_eip(
            instance_id="inst-1", public_ip_id="eip-1",
            confirm=True, plan_id=preview["plan_id"],
        )
    assert exc_info.value.code == "MCP_GUARDRAIL_BLOCKED"


async def test_bind_eip_preview_contains_address_and_warnings(network) -> None:
    service, _, _, _ = network
    preview = await service.bind_eip(instance_id="inst-1", public_ip_id="eip-1")
    assert preview["changes"]["public_ip"] == "1.2.3.4"
    assert any("internet" in w for w in preview["warnings"])


async def test_unbind_eip_requires_existing_public_ip(network) -> None:
    service, _, _, _ = network
    with pytest.raises(McpToolError) as exc_info:
        await service.unbind_eip(instance_id="inst-1")
    assert exc_info.value.code == "MCP_INVALID_ARGS"
