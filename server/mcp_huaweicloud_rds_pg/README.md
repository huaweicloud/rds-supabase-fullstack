# mcp_server_rds_pg

华为云 RDS for PostgreSQL 实例管理 MCP Server（v1.0.0，M1-M4b 全量 74 工具，配套 Skill：skills/database/rds/huaweicloud-rds-pg-ops）。

## 架构

遵循 rds-supabase-fullstack 仓库三层铁律：

```
tools/    @mcp.tool()+@guard 极薄注册（禁 import SDK）
service/  场景编排：两段式管线（mutate.py）、PlanStore 账本（plans.py）
client/   SDK 薄封装（asyncio.to_thread）
```

护栏由 `huaweicloud_mcp_core.build_server` 自动挂载：只读模式、风险声明校验、
保护规则、输出脱敏（不可关）、JSONL 审计。

## 两段式提交

所有写类工具（DANGEROUS/WRITE）统一走 `service/mutate.py` 的 `run_mutation` 管线：

1. **预览**：`confirm=false` → 返回 changes + warnings + plan_id（10 分钟 TTL、单次使用）
2. **提交**：同参数 + `confirm=true` + `plan_id` → claim（digest 校验：参数变更/跨实例嫁接/重放全部拒绝）→ 提交前回查实例状态（ACTIVE 且无 action 锁）→ 执行 → 错误三分类（明确拒绝→failed 可重试；结果不明→unknown 禁止重放）

环境双开关（写操作默认开启，开箱即用）：`RDS_PG_ENABLE_WRITES` 缺省 true；设 false 可关闭写。`HUAWEICLOUD_MCP_READ_ONLY=true` 仍是全局只读熔断。

## 环境变量

| 变量 | 说明 |
|---|---|
| `HUAWEICLOUD_ACCESS_KEY` / `HUAWEICLOUD_SECRET_KEY` | AK/SK（必需） |
| `HUAWEICLOUD_REGION` | 区域，如 `cn-north-4`（必需） |
| `HUAWEICLOUD_PROJECT_ID` | 可选，缺省经 IAM 自动解析 |
| `HUAWEICLOUD_MCP_READ_ONLY` | `true` 拦截一切写操作 |
| `RDS_PG_ENABLE_WRITES` | 缺省 `true`（开箱即用）；设 `false` 禁写 |
| `RDS_PG_STATE_FILE` | PlanStore 路径（默认 `~/.local/state/huaweicloud-rds-pg/plans.sqlite3`） |
| `HUAWEICLOUD_MCP_PROTECTED_IDS/NAMES/TAGS` | 资源保护规则 |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | 审计 JSONL 文件（stderr 始终输出） |

## 运行

```bash
uv sync
uv run mcp-huaweicloud-rds-pg          # stdio
uv run mcp-huaweicloud-rds-pg -t streamable-http   # HTTP :8000
```

## 测试

```bash
uv run ruff check && uv run mypy && uv run pytest --cov
```

## v0.1 工具（P0-1 实例生命周期子集）

| 工具 | 风险 | 说明 |
|---|---|---|
| list_pg_instances | READ | 实例清单（分页） |
| show_pg_instance | READ | 单实例详情 |
| show_pg_instance_job | READ | 异步 job 回查 |
| reboot_pg_instance | DANGEROUS | 重启（两段式） |
| stop_pg_instance | DANGEROUS | 停机，仅 postPaid（两段式） |
| start_pg_instance | DANGEROUS | 启动（两段式） |

范围外（已决策移除，不实现）：删实例、删手动备份、恢复到新实例、PITR 恢复。

## 里程碑

- M1（本版）：骨架 + PlanStore + mutate 管线 + 实例生命周期工具
- M2：P0 全量（创建编排 plan_pg_instance_creation、连接、备份恢复、库账号）
- M3：P1 全量 + Skill `huawei-cloud-rds-pg-ops`
