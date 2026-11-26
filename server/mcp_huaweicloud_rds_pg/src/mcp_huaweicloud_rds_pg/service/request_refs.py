# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Request-file indirection for secrets (passwords).

Secrets never enter the conversation: the agent writes a local request file
(0600) containing the secret, then passes its path as a ``*_ref`` argument.
Tools read the file server-side at submit time; previews show only the
reference, never the value.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from huaweicloud_mcp_core.errors import McpToolError

_REQUESTS_DIR = Path(
    os.getenv(
        "RDS_PG_REQUESTS_DIR",
        str(Path.home() / ".local/state/huaweicloud-rds-pg/requests"),
    )
)

_MAX_FILE_BYTES = 64 * 1024
_VALID_KEYS = {
    "password",  # instance admin / db user passwords
}


def write_request(fields: dict[str, Any]) -> dict[str, Any]:
    """Persist secrets to a new 0600 request file; return the reference view."""
    unknown = set(fields) - _VALID_KEYS
    if unknown:
        raise McpToolError(
            "MCP_INVALID_ARGS",
            f"Unsupported request fields: {sorted(unknown)}",
            hint=f"Supported fields: {sorted(_VALID_KEYS)}",
        )
    _REQUESTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = f"req-{os.urandom(8).hex()}.json"
    path = _REQUESTS_DIR / name
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(fields, fh)
    os.chmod(path, 0o600)
    return {
        "request_ref": str(path),
        "fields": sorted(fields),
        "note": "Secret values live only in this local file (0600); pass the "
        "request_ref path to the tool. Never print the file contents.",
    }


def read_request(request_ref: str) -> dict[str, Any]:
    """Load and validate a request file referenced at submit time."""
    path = Path(request_ref)
    if not path.is_absolute():
        raise McpToolError(
            "MCP_INVALID_ARGS",
            "request_ref must be an absolute path from write_pg_secret_request",
        )
    if path.is_symlink():
        raise McpToolError("MCP_GUARDRAIL_BLOCKED", "Request file must not be a symlink")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise McpToolError(
            "MCP_NOT_FOUND",
            f"Request file not found: {request_ref}",
            hint="Create one with write_pg_secret_request first.",
        ) from exc
    if os.name != "nt" and mode & 0o077:
        # POSIX-only: on Windows/NTFS stat() maps ACLs to a constant 0o666 -
        # the bit check is meaningless there (ACL security is OS-managed).
        raise McpToolError(
            "MCP_GUARDRAIL_BLOCKED",
            "Request file permissions too open; expected 0600",
        )
    if path.stat().st_size > _MAX_FILE_BYTES:
        raise McpToolError("MCP_INVALID_ARGS", "Request file too large")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise McpToolError("MCP_INVALID_ARGS", "Request file is not valid JSON") from exc
    if not isinstance(data, dict) or not set(data) <= _VALID_KEYS:
        raise McpToolError(
            "MCP_INVALID_ARGS",
            "Request file contains unsupported fields",
            hint=f"Supported fields: {sorted(_VALID_KEYS)}",
        )
    return data


def preview_ref(request_ref: str | None) -> str | None:
    """Representation of the ref for preview envelopes (no values)."""
    if request_ref is None:
        return None
    return {
        "kind": "request_ref",
        "path": request_ref,
        "fields": "hidden",
    }  # type: ignore[return-value]
