# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""FastMCP instance construction for the RDS-PG server (guardrails auto-installed)."""

from huaweicloud_mcp_core.server import build_server
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = build_server("rds-pg")


@mcp.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health_check(_request: Request) -> JSONResponse:
    """Lightweight liveness probe used by the MCP client/agent.

    The standard MCP protocol runs on /mcp; clients that probe /health
    otherwise get a 404. This returns 200 {"status":"ok","service":"rds-pg"} so
    the agent's readiness check passes.
    """
    return JSONResponse({"status": "ok", "service": "rds-pg"})


# Tool modules register themselves via the @mcp.tool() import side effect.
# Registration order is intentional (scenario grouping) - do NOT sort alphabetically.
from mcp_server_rds_pg.tools import instance  # noqa: E402,F401
