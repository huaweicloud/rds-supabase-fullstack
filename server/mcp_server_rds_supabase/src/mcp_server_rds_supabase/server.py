"""RDS Supabase MCP server and tool registration."""

from huaweicloud_mcp_core import build_server

mcp = build_server("rds-supabase")

# Bottom-up registration. The import order below is the upstream TypeScript
# tool registration order (database, project, auth_users, storage, platform,
# inspection) and must not be sorted alphabetically.
from .tools import (  # noqa: E402,F401  # isort: skip
    database,
    project,
    auth_users,
    storage,
    platform,
    inspection,
)
