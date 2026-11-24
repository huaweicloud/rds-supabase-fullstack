# MCP 服务器安装与注册

> 何时读：首次接入本技能族、或需要在新的宿主（Claude Code/Cursor）注册 MCP 服务器时。

## 安装（唯一合法来源）

```bash
# 从本仓安装（禁止 PyPI 同名第三方包——凭据安全）
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_pg
uv sync
uv run pytest -q --no-cov     # 冒烟：38 passed
```

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `HUAWEICLOUD_ACCESS_KEY` / `HUAWEICLOUD_SECRET_KEY` | ✅ | IAM 凭证 |
| `HUAWEICLOUD_REGION` | ✅ | 如 cn-north-4 |
| `HUAWEICLOUD_PROJECT_ID` | 可选 | 缺省经 IAM 自动解析 |
| `HUAWEICLOUD_MCP_READ_ONLY` | 建议首跑 true | 拦截一切写操作 |
| `RDS_PG_ENABLE_WRITES` | 写操作前 true | 两段式提交开关 |
| `RDS_PG_STATE_FILE` | 可选 | PlanStore 路径（默认 ~/.local/state/huaweicloud-rds-pg/plans.sqlite3） |
| `HUAWEICLOUD_MCP_PROTECTED_IDS/NAMES` | 可选 | 生产实例保护规则（读放行写拦截） |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | 可选 | 审计 JSONL 文件（stderr 始终输出） |

## Claude Code 注册（项目级 .mcp.json）

```json
{
  "mcpServers": {
    "rds-pg": {
      "command": "uv",
      "args": ["run", "--directory", "<绝对路径>/server/mcp_server_rds_pg", "mcp-huaweicloud-rds-pg"],
      "env": {
        "HUAWEICLOUD_ACCESS_KEY": "...",
        "HUAWEICLOUD_SECRET_KEY": "...",
        "HUAWEICLOUD_REGION": "cn-north-4"
      }
    }
  }
}
```

## 启动方式

```bash
uv run mcp-huaweicloud-rds-pg                       # stdio（注册后宿主自动拉起）
uv run mcp-huaweicloud-rds-pg -t streamable-http   # HTTP :8000（/health 探活）
```

## 首次接入验证序列

1. `list_pg_instances` → 只读通路 OK（返回 PG 实例列表）
2. `show_pg_quotas` → 配额可见
3. READ_ONLY=true 下调 `reboot_pg_instance` → 应返回 MCP_READ_ONLY（护栏生效）
4. 放开写开关后跑一次预览（confirm=false）→ confirmation_required + plan_id（两段式生效）
