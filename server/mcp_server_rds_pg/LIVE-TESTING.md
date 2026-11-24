# 现网测试指引（华为云 RDS for PostgreSQL）

## 1. 安装

```bash
cd server/mcp_server_rds_pg
uv sync
uv run mcp-huaweicloud-rds-pg            # stdio 模式
uv run mcp-huaweicloud-rds-pg -t streamable-http   # HTTP :8000
```

## 2. 环境变量（现网凭证）

```bash
export HUAWEICLOUD_ACCESS_KEY=<你的AK>
export HUAWEICLOUD_SECRET_KEY=<你的SK>
export HUAWEICLOUD_REGION=cn-north-4        # 按实际区域
# 可选：
export HUAWEICLOUD_PROJECT_ID=<项目ID>      # 缺省经 IAM 自动解析
```

## 3. 测试矩阵（由浅入深）

| 步骤 | 工具 | 预期 |
|---|---|---|
| 1 只读 | list_pg_instances | 返回当前区域实例列表（无实例返回空 items） |
| 2 只读 | show_pg_instance <id> | 单实例详情（status/引擎/flavor） |
| 3 只读 | show_pg_instance_job <id> | 任意历史 job 查询 |
| 4 两段式 | reboot_pg_instance confirm=false | 返回 confirmation_required + plan_id + warnings |
| 5 两段式 | 同参 + confirm=true + plan_id | 提交返回 job_id（**注意：真会重启实例！选测试实例**） |
| 6 护栏 | 同上但 HUAWEICLOUD_MCP_READ_ONLY=true | 返回 MCP_READ_ONLY 拒绝 |
| 7 防重放 | 提交后再用同 plan_id | 返回 MCP_GUARDRAIL_BLOCKED |

## 4. 写开关

写操作默认关闭。测试两段式前需要：
```bash
export RDS_PG_ENABLE_WRITES=true
unset HUAWEICLOUD_MCP_READ_ONLY
```

## 5. 已知限制（M1 范围）

- 仅 6 个工具：list/show/show_job + reboot/stop/start
- 删除/备份恢复/建库建账号等在 M2
- stop 仅对按需（postPaid）实例有效
- PlanStore 状态文件在 ~/.local/state/huaweicloud-rds-pg/plans.sqlite3

## 6. MCP 客户端注册（Claude Code）

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
