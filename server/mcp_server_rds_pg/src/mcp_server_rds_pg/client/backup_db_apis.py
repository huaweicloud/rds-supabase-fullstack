# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""P0-3/P0-4 client APIs: backup management and PG database/user operations."""

from __future__ import annotations

from typing import Any, cast

from huaweicloud_mcp_core.errors import wrap_sdk_error
from huaweicloudsdkcore.exceptions.exceptions import SdkException

from mcp_server_rds_pg.client.throttle import guarded_call


def _to_dict(obj: Any) -> Any:
    from mcp_server_rds_pg.client.sdk_rds import sdk_to_dict

    return sdk_to_dict(obj)


class BackupMixin:
    _client: Any

    async def show_backup_policy(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.show_backup_policy_request import (
                ShowBackupPolicyRequest,
            )

            request = ShowBackupPolicyRequest(instance_id=instance_id)
            return cast(dict[str, Any], _to_dict(self._client.show_backup_policy(request)))

        return await guarded_call("sdk", _call)

    async def set_backup_policy(
        self, *, instance_id: str, keep_days: int, start_time: str, period: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.backup_policy import BackupPolicy
            from huaweicloudsdkrds.v3.model.set_backup_policy_request import (
                SetBackupPolicyRequest,
            )
            from huaweicloudsdkrds.v3.model.set_backup_policy_request_body import (
                SetBackupPolicyRequestBody,
            )

            body = SetBackupPolicyRequestBody(
                backup_policy=BackupPolicy(
                    keep_days=str(keep_days), start_time=start_time, period=period
                )
            )
            request = SetBackupPolicyRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.set_backup_policy(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)

    async def create_manual_backup(
        self, *, instance_id: str, name: str, description: str | None = None
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_manual_backup_request import (
                CreateManualBackupRequest,
            )
            from huaweicloudsdkrds.v3.model.create_manual_backup_request_body import (
                CreateManualBackupRequestBody,
            )

            body = CreateManualBackupRequestBody(
                instance_id=instance_id, name=name, description=description
            )
            request = CreateManualBackupRequest(body=body)
            try:
                return cast(
                    dict[str, Any], _to_dict(self._client.create_manual_backup(request))
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)

    async def list_backups(
        self,
        *,
        instance_id: str,
        backup_type: str | None = None,
        limit: int = 20,
        offset: int | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_backups_request import (
                ListBackupsRequest,
            )

            request = ListBackupsRequest(
                instance_id=instance_id,
                backup_type=backup_type,
                limit=limit,
                offset=offset,
            )
            return cast(dict[str, Any], _to_dict(self._client.list_backups(request)))

        return await guarded_call("sdk", _call)

    async def show_backup_download_link(self, *, backup_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.show_backup_download_link_request import (
                ShowBackupDownloadLinkRequest,
            )

            request = ShowBackupDownloadLinkRequest(backup_id=backup_id)
            return cast(
                dict[str, Any],
                _to_dict(self._client.show_backup_download_link(request)),
            )

        return await guarded_call("sdk", _call)

    async def list_restore_times(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_restore_times_request import (
                ListRestoreTimesRequest,
            )

            request = ListRestoreTimesRequest(instance_id=instance_id)
            return cast(
                dict[str, Any], _to_dict(self._client.list_restore_times(request))
            )

        return await guarded_call("sdk", _call)


class PgDatabaseMixin:
    _client: Any

    async def list_pg_databases(
        self, *, instance_id: str, page: int = 1, limit: int = 100
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_postgresql_databases_request import (
                ListPostgresqlDatabasesRequest,
            )

            request = ListPostgresqlDatabasesRequest(
                instance_id=instance_id, page=page, limit=limit
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.list_postgresql_databases(request)),
            )

        return await guarded_call("sdk", _call)

    async def create_pg_database(
        self, *, instance_id: str, name: str, owner: str | None = None,
        character_set: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_postgresql_database_request import (
                CreatePostgresqlDatabaseRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_database_for_creation import (
                PostgresqlDatabaseForCreation,
            )

            body = PostgresqlDatabaseForCreation(
                name=name, owner=owner, character_set=character_set
            )
            request = CreatePostgresqlDatabaseRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_postgresql_database(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)

    async def list_pg_schemas(self, *, instance_id: str, db_name: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_postgresql_database_schemas_request import (
                ListPostgresqlDatabaseSchemasRequest,
            )

            request = ListPostgresqlDatabaseSchemasRequest(
                instance_id=instance_id, db_name=db_name, page=1, limit=100
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.list_postgresql_database_schemas(request)),
            )

        return await guarded_call("sdk", _call)

    async def create_pg_schema(
        self, *, instance_id: str, db_name: str, schema_name: str,
        owner: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_postgresql_database_schema_request import (
                CreatePostgresqlDatabaseSchemaRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_create_schema_req import (
                PostgresqlCreateSchemaReq,
            )
            from huaweicloudsdkrds.v3.model.postgresql_database_schema_req import (
                PostgresqlDatabaseSchemaReq,
            )

            body = PostgresqlDatabaseSchemaReq(
                db_name=db_name,
                schemas=[PostgresqlCreateSchemaReq(schema_name=schema_name, owner=owner)],
            )
            request = CreatePostgresqlDatabaseSchemaRequest(
                instance_id=instance_id, body=body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_postgresql_database_schema(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)

    async def list_pg_db_users(self, *, instance_id: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.list_postgresql_db_user_paginated_request import (
                ListPostgresqlDbUserPaginatedRequest,
            )

            request = ListPostgresqlDbUserPaginatedRequest(
                instance_id=instance_id, page=1, limit=100
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.list_postgresql_db_user_paginated(request)),
            )

        return await guarded_call("sdk", _call)

    async def create_pg_db_user(
        self, *, instance_id: str, name: str, password: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.create_postgresql_db_user_request import (
                CreatePostgresqlDbUserRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_user_for_creation import (
                PostgresqlUserForCreation,
            )

            body = PostgresqlUserForCreation(
                name=name, password=password, comment=comment
            )
            request = CreatePostgresqlDbUserRequest(instance_id=instance_id, body=body)
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.create_postgresql_db_user(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)

    async def set_pg_db_user_password(
        self, *, instance_id: str, name: str, password: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.db_user_pwd_request import DbUserPwdRequest
            from huaweicloudsdkrds.v3.model.set_postgresql_db_user_pwd_request import (
                SetPostgresqlDbUserPwdRequest,
            )

            body = DbUserPwdRequest(name=name, password=password)
            request = SetPostgresqlDbUserPwdRequest(
                instance_id=instance_id, body=body
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.set_postgresql_db_user_pwd(request)),
            )

        return await guarded_call("sdk", _call)

    async def update_pg_db_user_comment(
        self, *, instance_id: str, name: str, comment: str
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.update_postgresql_db_user_comment_request import (
                UpdatePostgresqlDbUserCommentRequest,
            )
            from huaweicloudsdkrds.v3.model.update_postgresql_db_user_comment_request_body import (
                UpdatePostgresqlDbUserCommentRequestBody,
            )

            body = UpdatePostgresqlDbUserCommentRequestBody(comment=comment)
            request = UpdatePostgresqlDbUserCommentRequest(
                instance_id=instance_id, name=name, body=body
            )
            return cast(
                dict[str, Any],
                _to_dict(self._client.update_postgresql_db_user_comment(request)),
            )

        return await guarded_call("sdk", _call)

    async def grant_pg_db_privilege(
        self, *, instance_id: str, db_name: str, users: list[dict[str, Any]]
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            from huaweicloudsdkrds.v3.model.allow_db_privilege_request import (
                AllowDbPrivilegeRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_grant_request import (
                PostgresqlGrantRequest,
            )
            from huaweicloudsdkrds.v3.model.postgresql_user_with_privilege import (
                PostgresqlUserWithPrivilege,
            )

            grant_body = PostgresqlGrantRequest(
                db_name=db_name,
                users=[PostgresqlUserWithPrivilege(**u) for u in users],
            )
            request = AllowDbPrivilegeRequest(
                instance_id=instance_id, body=grant_body
            )
            try:
                return cast(
                    dict[str, Any],
                    _to_dict(self._client.allow_db_privilege(request)),
                )
            except SdkException as exc:
                raise wrap_sdk_error(exc) from exc

        return await guarded_call("sdk", _call)
