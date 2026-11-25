# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Process-level SdkRdsClient reuse (P1-1 from PERF-SPEC.md §5).

Every tool call used to build a fresh SdkRdsClient, discarding the
requests Session's warm connection pool - each hop paid an extra TLS
handshake (~150-250ms; measured warm 45ms vs cold 264ms). The shared
factory caches one client per credential identity (ak, sk, token,
region); rotating credentials creates a new key and a new client.

Caveat (documented contract): the cache snapshot happens at first use;
changing AK/SK env vars mid-process requires an MCP restart - which is
already how hosts inject credentials.

Thread safety: SDK calls are serialized in-process by the 200ms
throttle gate (throttle.py), so a shared requests Session sees no
concurrent use in practice.
"""

from __future__ import annotations

from typing import Any

from mcp_server_rds_pg.client.sdk_rds import SdkRdsClient

_CLIENT_CACHE: dict[tuple[str, ...], Any] = {}


def _identity_key(ak: str, sk: str, token: str | None, region: str) -> tuple[str, ...]:
    return ("rds-pg", ak, sk, token or "", region)


def get_shared_client() -> SdkRdsClient:
    """Return the process-level shared SdkRdsClient for current env creds."""
    from huaweicloud_mcp_core.config import McpSettings

    settings = McpSettings.from_env()
    key = _identity_key(
        settings.access_key, settings.secret_key, settings.security_token, settings.region
    )
    cached = _CLIENT_CACHE.get(key)
    if cached is None:
        cached = SdkRdsClient(settings)
        _CLIENT_CACHE[key] = cached
    return cached


def reset_client_cache() -> None:
    """Test hook: drop cached clients so a new identity is picked up."""
    _CLIENT_CACHE.clear()


def get_shared_ces_client() -> Any:
    """Process-level shared CES client (same reuse rationale)."""
    from huaweicloud_mcp_core.config import McpSettings

    from mcp_server_rds_pg.client.m3_apis import CesClient

    settings = McpSettings.from_env()
    key = ("ces",) + _identity_key(
        settings.access_key, settings.secret_key, settings.security_token, settings.region
    )
    cached = _CLIENT_CACHE.get(key)
    if cached is None:
        cached = CesClient(settings)
        _CLIENT_CACHE[key] = cached
    return cached
