# MCP 安装与配置指南

## 安装服务器

```bash
uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack \
  --subdirectory server/mcp_server_rds_supabase \
  mcp-server-huaweicloud-rds-supabase
```

或本地已克隆仓库时等价运行：`uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`（虚拟环境只生成于仓内目录；生产建议 pin `@<commit>`）。禁止 `pip install` / `uv tool install` 装入用户级或系统级环境——入口与包将跨项目可见，违反项目级隔离约束。

## 客户端配置（stdio）

```json
{
  "mcpServers": {
    "rds-supabase": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/huaweicloud/rds-supabase-fullstack",
        "--subdirectory", "server/mcp_server_rds_supabase",
        "mcp-server-huaweicloud-rds-supabase"
      ],
      "env": {
        "SUPABASE_URL": "https://your-instance",
        "SUPABASE_ANON_KEY": "<anon-key>",
        "SUPABASE_SERVICE_ROLE_KEY": "<service-key>"
      }
    }
  }
}
```

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| SUPABASE_URL | 是 | 网关基础 URL |
| SUPABASE_ANON_KEY | 是 | 匿名密钥 |
| SUPABASE_SERVICE_ROLE_KEY | 否 | 启用 RPC SQL 通道 |
| SUPABASE_AUTH_JWT_SECRET | 否 | verify_jwt_secret 检查 |
| RDS_SUPABASE_WORKSPACE_PATH | 否 | 文件输出工作区根 |
| RDS_SUPABASE_TOOLS_CONFIG | 否 | enabledTools JSON 白名单 |
| HUAWEICLOUD_MCP_READ_ONLY | 否 | 拦截全部 WRITE 工具 |
| HUAWEICLOUD_MCP_GUARDRAILS_CONFIG | 否 | block/confirm/warn 规则 |
| HUAWEICLOUD_MCP_PROTECTED_IDS/NAMES/TAGS | 否 | 保护名单 |
| HUAWEICLOUD_MCP_AUDIT_FILE | 否 | JSONL 审计文件 |
| MCP_SERVER_HOST / MCP_SERVER_PORT | 否 | streamable-http 监听 |

## execute_sql 函数部署

[`sql/mcp-execute-sql.sql`](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/sql/mcp-execute-sql.sql) 为加固版定义（仅 service_role、read_only 语句白名单），位于仓库 `server/mcp_server_rds_supabase/sql/` 下（技能包内不含 `server/` 目录，以上述 URL 为准）。经 psql 或管理通道部署一次即可；未部署时仅 execute_sql 不可用，其余工具不受影响。
