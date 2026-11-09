# Build from the repository root:
#   docker build -f server/mcp_server_rds_supabase/Dockerfile .
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app/server/mcp_server_rds_supabase

COPY libs/huaweicloud_mcp_core /app/libs/huaweicloud_mcp_core
COPY server/mcp_server_rds_supabase/pyproject.toml server/mcp_server_rds_supabase/uv.lock ./
COPY server/mcp_server_rds_supabase/README.md ./
COPY server/mcp_server_rds_supabase/src ./src

RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 mcp && chown -R mcp:mcp /app
USER mcp

ENV MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8000
EXPOSE 8000

ENTRYPOINT ["uv", "run", "--frozen", "--no-sync", "mcp-server-huaweicloud-rds-supabase"]
CMD ["-t", "streamable-http"]
