# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Shared fixtures for the RDS-PG server tests."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_huaweicloud_rds_pg.service.plans import PlanStore

_ENV_KEYS = [
    "HUAWEICLOUD_ACCESS_KEY",
    "HUAWEICLOUD_SECRET_KEY",
    "HUAWEICLOUD_REGION",
    "HUAWEICLOUD_PROJECT_ID",
    "HUAWEICLOUD_SECURITY_TOKEN",
    "HUAWEICLOUD_ENDPOINT",
    "HUAWEICLOUD_MCP_READ_ONLY",
    "HUAWEICLOUD_MCP_PROTECTED_IDS",
    "HUAWEICLOUD_MCP_PROTECTED_NAMES",
    "HUAWEICLOUD_MCP_PROTECTED_TAGS",
    "HUAWEICLOUD_MCP_GUARDRAILS_CONFIG",
    "HUAWEICLOUD_MCP_AUDIT_FILE",
    "RDS_PG_STATE_FILE",
    "RDS_PG_ENABLE_WRITES",
    "MCP_SERVER_PORT",
    "MCP_SERVER_HOST",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def plans(tmp_path: Any) -> PlanStore:
    return PlanStore(path=str(tmp_path / "plans.sqlite3"))


class FakeSdkRdsClient:
    """In-memory fake of the SdkRdsClient interface used by service tests."""

    def __init__(self) -> None:
        self.instances: dict[str, dict[str, Any]] = {}
        self.jobs: dict[str, dict[str, Any]] = {}
        self.dns: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.reboot_result: dict[str, Any] = {"job_id": "job-reboot-1"}

    def _register_defaults(self) -> None:
        self.instances.setdefault(
            "inst-1",
            {
                "id": "inst-1",
                "name": "pg-dev",
                "status": "ACTIVE",
                "current_actions": [],
                "datastore": {"type": "PostgreSQL", "version": "16.15"},
                "flavor_ref": "rds.pg.n1.large.2.ha",
                "volume": {"type": "ULTRAHIGH", "size": 100},
                "ha": {"mode": "Ha", "replication_mode": "async"},
                "charge_info": {"charge_mode": "postPaid"},
                "private_ips": ["192.168.0.7"],
                "public_ips": [],
                "port": 5432,
                "type": "Ha",
            },
        )

    async def list_instances(
        self, *, limit: int, offset: int | None = None,
        id: str | None = None, name: str | None = None
    ) -> dict[str, Any]:
        self.calls.append(
            ("list_instances", {"limit": limit, "id": id, "name": name, "offset": offset})
        )
        items = list(self.instances.values())
        if id:
            items = [item for item in items if item["id"] == id]
        if name:
            items = [item for item in items if name.lower() in item["name"].lower()]
        return {"instances": items[:limit], "total": len(items)}

    async def list_job_info(self, *, job_id: str) -> dict[str, Any]:
        self.calls.append(("list_job_info", {"job_id": job_id}))
        job = self.jobs.get(job_id)
        if not job:
            return {"job": {}}
        return {"job": dict(job)}

    async def show_task_detail(self, *, job_id: str) -> dict[str, Any]:
        self.calls.append(("show_task_detail", {"job_id": job_id}))
        return self.jobs.get(job_id, {})

    async def list_ai_applications(self, *, limit: int = 100) -> dict[str, Any]:
        self.calls.append(("list_ai_applications", {"limit": limit}))
        return {"ai_applications": []}

    async def reboot_instance(self, *, instance_id: str) -> dict[str, Any]:
        self.calls.append(("reboot_instance", {"instance_id": instance_id}))
        return dict(self.reboot_result)

    async def stop_instance(self, *, instance_id: str) -> dict[str, Any]:
        self.calls.append(("stop_instance", {"instance_id": instance_id}))
        self.instances[instance_id]["status"] = "STOPPED"
        return {"job_id": "job-stop-1"}

    async def start_instance(self, *, instance_id: str) -> dict[str, Any]:
        self.calls.append(("start_instance", {"instance_id": instance_id}))
        self.instances[instance_id]["status"] = "ACTIVE"
        return {"job_id": "job-start-1"}

    async def show_dns_name(self, *, instance_id: str, dns_type: str = "private") -> dict[str, Any]:
        self.calls.append(("show_dns_name", {"instance_id": instance_id}))
        return self.dns.get(instance_id) or {
            "instance_id": instance_id,
            "dns_name": None,
            "dns_type": None,
            "status": None,
        }

    async def create_dns_name(
        self, *, instance_id: str, dns_type: str = "private"
    ) -> dict[str, Any]:
        self.calls.append(
            ("create_dns_name", {"instance_id": instance_id, "dns_type": dns_type})
        )
        self.dns[instance_id] = {
            "instance_id": instance_id,
            "dns_name": f"{instance_id}.internal.pg.rds.huaweicloud.com",
            "dns_type": dns_type,
            "status": "ACTIVE",
        }
        return {"job_id": "job-dns-create-1"}

    async def update_dns_name(
        self, *, instance_id: str, dns_name: str
    ) -> dict[str, Any]:
        self.calls.append(
            ("update_dns_name", {"instance_id": instance_id, "dns_name": dns_name})
        )
        if instance_id not in self.dns:
            self.dns[instance_id] = {"instance_id": instance_id, "dns_type": "private"}
        self.dns[instance_id]["dns_name"] = dns_name
        return {"job_id": "job-dns-update-1"}


@pytest.fixture
def fake_client() -> FakeSdkRdsClient:
    client = FakeSdkRdsClient()
    client._register_defaults()
    return client
