# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""M2 services: backup management (P0-3) and database/account (P0-4)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.output import clamp_limit, page_result, single_result

from mcp_huaweicloud_rds_pg.client.shared_client import get_shared_client

if TYPE_CHECKING:
    from mcp_huaweicloud_rds_pg.client.sdk_rds import SdkRdsClient
from mcp_huaweicloud_rds_pg.service.mutate import run_mutation
from mcp_huaweicloud_rds_pg.service.plans import PlanStore
from mcp_huaweicloud_rds_pg.service.request_refs import read_request

_BACKUP_FIELDS = ("id", "name", "type", "size", "status", "begin_time", "end_time")


class BackupService:
    """P0-3: policy, manual backups, downloads, restore windows."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def show_policy(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.show_backup_policy(instance_id=instance_id)
        policy = response.get("backup_policy") or response
        return single_result(policy)

    async def set_policy(
        self,
        *,
        instance_id: str,
        keep_days: int,
        start_time: str,
        period: str,
        confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        if keep_days < 7:
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "keep_days must be >= 7 (minimum retention)",
            )
        return await run_mutation(
            tool_name="set_pg_backup_policy",
            instance_id=instance_id,
            operation="set_backup_policy",
            body={
                "instance_id": instance_id,
                "keep_days": keep_days,
                "start_time": start_time,
                "period": period,
            },
            notices={
                "warnings": [
                    "Longer retention increases backup storage usage "
                    "(billed beyond the free quota).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.set_backup_policy(
                instance_id=instance_id,
                keep_days=keep_days,
                start_time=start_time,
                period=period,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def create_manual_backup(
        self, *, instance_id: str, name: str, description: str | None,
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        # Param-layer validation (fail before the preview/claim cycle):
        # RDS backup names must be 4-64 chars of letters/digits/hyphens/
        # underscores, starting with a letter - reject locally instead of
        # burning a cloud round-trip on garbage.
        import re

        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{3,63}", name or ""):
            raise McpToolError(
                "MCP_INVALID_ARGS",
                "Backup name must be 4-64 characters, start with a letter,"
                " and contain only letters/digits/hyphens/underscores",
                hint=f"Got: {name!r}",
            )
        return await run_mutation(
            tool_name="create_pg_manual_backup",
            instance_id=instance_id,
            operation="manual_backup",
            body={
                "instance_id": instance_id,
                "name": name,
                "description": description,
            },
            notices={
                "warnings": [
                    "Manual backups occupy storage until they expire or are "
                    "removed (billed beyond the free quota).",
                ]
            },
            recheck=True,
            execute=lambda: self._client.create_manual_backup(
                instance_id=instance_id, name=name, description=description
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_backups(
        self, *, instance_id: str, backup_type: str | None, limit: int,
        offset: int | None,
    ) -> dict[str, Any]:
        limit = clamp_limit(limit)
        response = await self._client.list_backups(
            instance_id=instance_id,
            backup_type=backup_type,
            limit=limit,
            offset=offset,
        )
        backups = [
            {k: b.get(k) for k in _BACKUP_FIELDS if b.get(k) is not None}
            for b in response.get("backups") or []
        ]
        total = response.get("total")
        return page_result(
            backups, total=int(total) if total is not None else None, marker=None
        )

    async def download_backup(self, *, backup_id: str) -> dict[str, Any]:
        response = await self._client.show_backup_download_link(backup_id=backup_id)
        link = response.get("file_path") or response.get("download_link")
        if not link:
            raise McpToolError(
                "MCP_NOT_FOUND",
                f"No download link for backup {backup_id} (still building?)",
            )
        return single_result(
            {"backup_id": backup_id, "download_link": link},
            hints=["Temporary URL - download promptly."],
        )

    async def list_restore_times(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.list_restore_times(instance_id=instance_id)
        times = response.get("restore_time") or []
        return page_result(times, total=len(times))


class PgDatabaseService:
    """P0-4: databases, schemas, users, privileges."""

    def __init__(
        self, client: SdkRdsClient | None = None, plans: PlanStore | None = None
    ) -> None:
        self._client = client or get_shared_client()
        self._plans = plans or PlanStore()

    async def list_databases(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.list_pg_databases(instance_id=instance_id)
        databases = response.get("databases") or []
        return page_result(databases, total=len(databases))

    async def create_database(
        self,
        *,
        instance_id: str,
        name: str,
        owner: str | None,
        character_set: str | None,
        confirm: bool,
        plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="create_pg_database",
            instance_id=instance_id,
            operation="create_database",
            body={
                "instance_id": instance_id,
                "name": name,
                "owner": owner,
                "character_set": character_set,
            },
            notices={},
            recheck=True,
            execute=lambda: self._client.create_pg_database(
                instance_id=instance_id,
                name=name,
                owner=owner,
                character_set=character_set,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_schemas(self, *, instance_id: str, db_name: str) -> dict[str, Any]:
        response = await self._client.list_pg_schemas(
            instance_id=instance_id, db_name=db_name
        )
        schemas = response.get("schemas") or []
        return page_result(schemas, total=len(schemas))

    async def create_schema(
        self, *, instance_id: str, db_name: str, schema_name: str,
        owner: str | None, confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        return await run_mutation(
            tool_name="create_pg_schema",
            instance_id=instance_id,
            operation="create_schema",
            body={
                "instance_id": instance_id,
                "db_name": db_name,
                "schema_name": schema_name,
            },
            notices={},
            recheck=True,
            execute=lambda: self._client.create_pg_schema(
                instance_id=instance_id, db_name=db_name, schema_name=schema_name,
                owner=owner,
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def list_users(self, *, instance_id: str) -> dict[str, Any]:
        response = await self._client.list_pg_db_users(instance_id=instance_id)
        users = response.get("users") or []
        return page_result(users, total=len(users))

    async def create_user(
        self, *, instance_id: str, name: str, password_ref: str,
        comment: str | None, confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        secrets = read_request(password_ref)
        password = secrets.get("password")
        if not password:
            raise McpToolError("MCP_INVALID_ARGS", "Request file lacks the password field")
        return await run_mutation(
            tool_name="create_pg_db_user",
            instance_id=instance_id,
            operation="create_user",
            body={
                "instance_id": instance_id,
                "name": name,
                "password_ref": password_ref,
                "comment": comment,
            },
            notices={
                "warnings": [
                    "The password value stays in the local request file; it never "
                    "appears in results or audit logs.",
                ]
            },
            recheck=True,
            execute=lambda: self._client.create_pg_db_user(
                instance_id=instance_id, name=name, password=password, comment=comment
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def set_user_password(
        self, *, instance_id: str, name: str, password_ref: str,
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        secrets = read_request(password_ref)
        password = secrets.get("password")
        if not password:
            raise McpToolError("MCP_INVALID_ARGS", "Request file lacks the password field")
        return await run_mutation(
            tool_name="set_pg_db_user_password",
            instance_id=instance_id,
            operation="set_password",
            body={
                "instance_id": instance_id,
                "name": name,
                "password_ref": password_ref,
            },
            notices={
                "warnings": ["Existing sessions with the old password fail on next use."]
            },
            recheck=True,
            execute=lambda: self._client.set_pg_db_user_password(
                instance_id=instance_id, name=name, password=password
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )

    async def update_user_comment(
        self, *, instance_id: str, name: str, comment: str
    ) -> dict[str, Any]:
        """L1 light write: synchronous, reversible - middleware confirm only."""
        response = await self._client.update_pg_db_user_comment(
            instance_id=instance_id, name=name, comment=comment
        )
        return single_result(response or {"result": "updated"})

    async def grant_privilege(
        self, *, instance_id: str, db_name: str, users: list[dict[str, Any]],
        confirm: bool, plan_id: str | None,
    ) -> dict[str, Any]:
        for user in users:
            if "name" not in user or "readonly" not in user:
                raise McpToolError(
                    "MCP_INVALID_ARGS",
                    "each grant user needs name and readonly (true/false)",
                )
            # Auto-fill the target schema (cloud API rejects grant calls
            # without one); echo the resolved schema in preview and result.
            user.setdefault("schema_name", "public")
        return await run_mutation(
            tool_name="grant_pg_db_privilege",
            instance_id=instance_id,
            operation="grant",
            body={"instance_id": instance_id, "db_name": db_name, "users": users},
            notices={},
            recheck=True,
            execute=lambda: self._client.grant_pg_db_privilege(
                instance_id=instance_id, db_name=db_name, users=users
            ),
            plans=self._plans,
            client=self._client,
            confirm=confirm,
            plan_id=plan_id,
        )
