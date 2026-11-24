# 现网测试指引（华为云 RDS for PostgreSQL）

> M1 版本。测试分两个维度：**机制测试**（验证 MCP 框架能力：两段式/护栏/账本）和
> **业务场景测试**（验证用户视角的真实运维旅程）。

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

## 3. 机制测试矩阵（框架能力验证）

| 步骤 | 工具 | 预期 |
|---|---|---|
| 1 只读 | list_pg_instances | 返回当前区域实例列表（无实例返回空 items） |
| 2 只读 | show_pg_instance <id> | 单实例详情（status/引擎/flavor） |
| 3 只读 | show_pg_instance_job <id> | 任意历史 job 查询 |
| 4 两段式 | reboot_pg_instance confirm=false | 返回 confirmation_required + plan_id + warnings |
| 5 两段式 | 同参 + confirm=true + plan_id | 提交返回 job_id（**注意：真会重启实例！选测试实例**） |
| 6 护栏 | 同上但 HUAWEICLOUD_MCP_READ_ONLY=true | 返回 MCP_READ_ONLY 拒绝 |
| 7 防重放 | 提交后再用同 plan_id | 返回 MCP_GUARDRAIL_BLOCKED |

## 3B. 业务场景测试（用户旅程验证）

以真实运维场景为主线串联工具，验证「Agent 按场景指引能否走通完整旅程」。
每个场景对应设计文档的 P0 场景编号，是 Skill 编写前的需求验证。

### 场景 B1：日常巡检（P0-1 + P1-7 雏形，只读，无风险）

**用户故事**：「每天早上给我一份 PG 实例健康简报」

| 步 | 操作 | 验收 |
|---|---|---|
| B1.1 | `list_pg_instances` 全量 | 拿到实例清单，与控制台实例管理页逐字段核对（数量/status/AZ/规格） |
| B1.2 | 对每个实例 `show_pg_instance` | 关键字段正确：datastore.version、flavor_ref、volume.size、ha.mode、charge_mode |
| B1.3 | 检查 action 锁 | current_actions 为空的实例 = 可操作；非空的记录在简报里 |
| B1.4 | 编写简报输出 | Agent 能基于上述数据生成：实例数/异常状态数/锁定实例清单 |

**覆盖验证点**：列表分页信封、字段映射与控制台一致性、action 锁语义。

### 场景 B2：故障自愈重启（P0-1，两段式全流程）

**用户故事**：「实例假死，帮我重启恢复」

| 步 | 操作 | 验收 |
|---|---|---|
| B2.1 | `show_pg_instance <id>` 确认现状 | status 为 ACTIVE 或异常态，记录 current_actions |
| B2.2 | `reboot_pg_instance confirm=false` | 预览信封含 warnings（中断连接提示）；**实例未动**（控制台刷新确认） |
| B2.3 | 模拟「用户犹豫改了主意」：放弃该 plan_id | 不提交，10 分钟后该 plan 自然过期（可跳过等待，逻辑已被单测覆盖） |
| B2.4 | 重新预览 + `confirm=true` 提交 | 返回 job_id；控制台实例变 REBOOTING |
| B2.5 | `show_pg_instance_job` 轮询（30s×20） | status 走向 Completed |
| B2.6 | `show_pg_instance` 复核 | status 回 ACTIVE、无 current_actions |
| B2.7 | 重启期间再发一个预览 | 提交时应被 action 锁拦截（MCP_GUARDRAIL_BLOCKED: not demonstrably ready） |

**覆盖验证点**：两段式全链、job 轮询、TOCTOU 回查（action 锁）。

### 场景 B3：成本优化停机（P0-1，计费语义验证）

**用户故事**：「周末不用的开发实例停掉省钱，周一再开」

| 步 | 操作 | 验收 |
|---|---|---|
| B3.1 | 对按需实例 `stop_pg_instance` 两段式 | 提交成功，实例 STOPPED |
| B3.2 | 停机后 `show_pg_instance` | 状态正确；**预览信封中的 warning「停机仍计存储费」出现了** |
| B3.3 | 停机状态下 psql 连接实例 | 连接失败（真实中断验证） |
| B3.4 | 对包周期实例调 stop | `MCP_INVALID_ARGS`（prePaid 拒绝）——计费语义正确 |
| B3.5 | `start_pg_instance` 两段式恢复 | 回 ACTIVE，psql 可连 |
| B3.6 | start 走两段式但目标实例已是 ACTIVE | 提交被 ACTIVE 回查拦截（非 ACTIVE 才是 start 的合法目标） |

**覆盖验证点**：计费模式分流、停机真实效果、start 的状态前置。

### 场景 B4：异常输入与边界（鲁棒性）

**用户故事**：Agent 被用户输入错误信息时的行为

| 步 | 操作 | 验收 |
|---|---|---|
| B4.1 | `show_pg_instance` 不存在 id | `MCP_NOT_FOUND` 信封，hint 引导先 list |
| B4.2 | `reboot` 空 id / 非法字符 | 参数校验拒绝，不产生 SDK 调用 |
| B4.3 | `show_pg_instance_job` 无效 job id | `MCP_NOT_FOUND` 或空 job 信封，不崩溃 |
| B4.4 | list limit=0 / limit=999 / 负数 | 夹紧到 1..100，不报错 |
| B4.5 | 凭证错误（错 AK） | 错误信封含 request_id，提示权限/凭证问题 |
| B4.6 | 区域无实例的账号 | 空列表正常返回 |

**覆盖验证点**：错误信封统一格式、参数夹紧、SDK 异常 wrap。

### 场景 B5：保护规则实战（护栏业务化）

**用户故事**：「生产实例绝不能被 Agent 动」

| 步 | 操作 | 验收 |
|---|---|---|
| B5.1 | `export HUAWEICLOUD_MCP_PROTECTED_IDS=<生产实例id>` 重启 server | 启动时 fail-fast 校验通过 |
| B5.2 | `show_pg_instance <生产id>` | READ 正常（保护规则不拦读） |
| B5.3 | `reboot_pg_instance <生产id> confirm=false` | 预览即被 block（参数级匹配命中） |
| B5.4 | 改用 `HUAWEICLOUD_MCP_PROTECTED_NAMES=<实例名>` 同样验证 | name 匹配生效 |

**覆盖验证点**：保护规则 id/name 两级匹配、读写不对称。

### 场景 B6：审计追溯（合规）

**用户故事**：「安全团队要查最近谁通过 MCP 动了实例」

| 步 | 操作 | 验收 |
|---|---|---|
| B6.1 | `export HUAWEICLOUD_MCP_AUDIT_FILE=/tmp/audit.jsonl` 重启 | 每次工具调用（含被拦的）写一条 |
| B6.2 | 跑一遍 B2 场景 | audit.jsonl 有完整记录：预览（allowed）→ 提交（allowed）→ action 锁拦截（blocked） |
| B6.3 | 检查 params 字段 | 已脱敏、长参数截断、无敏感值 |
| B6.4 | jsonl 可被 jq 解析 | 机器可读，含 tool/risk/decision/duration_ms |

**覆盖验证点**：审计完整性、脱敏、JSONL 可解析。

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
- B 场景中涉及 M2 工具的（创建实例/变配/备份）待 M2 后补充对应场景（B7+）

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

## 7. 测试结果记录模板

每场景一行，附失败详情：
```
B1 巡检: PASS（4/4 步）
B2 重启: PASS，B2.7 action 锁拦截验证: PASS
B3 停机: FAIL B3.4 —— 包周期实例未被拒绝，错误信封: {...}
B4 边界: PASS（6/6）
B5 保护: PASS
B6 审计: PASS，jq 解析正常
```
