# 验证方法（verification-method.md）

> 何时读：技能/MCP 服务器安装后首次验证；任何写操作完成后的复核；技能发版前的验收。

## 1. 概述

本技能是 **MCP 型技能**（工具经 MCP 协议调用，不走 `hcloud` 命令），验证体系对应规范三级验证（安装验证 → 配置验证 → 功能验证）并延伸为「连接验证 → 功能验证 → 验收五连验」。现网测试矩阵源：MCP 工程 `LIVE-TESTING.md`（G1-G6 机制组 + B1-B16 业务场景组）。

## 2. 第一级：连接验证（对应规范「安装验证 + 配置验证」）

| # | 检查 | 命令/操作 | 成功标准 |
|---|---|---|---|
| V1.1 | uv 环境可用 | `cd server/mcp_server_rds_pg && uv sync` | 依赖解析成功，无错误 |
| V1.2 | MCP 服务器可拉起 | `uv run mcp-huaweicloud-rds-pg` | stdio 启动不崩溃；`-t streamable-http` 下 `/health` 返回 200 |
| V1.3 | 宿主注册生效 | 宿主内 `tools/list` | 返回 74 工具，名称 `huaweicloud-rds-pg` |
| V1.4 | 凭证已配置（带外） | 宿主内调用 `list_pg_instances` | 返回 page_result 信封（非凭证错误）；凭证从未出现在对话中 |
| V1.5 | 只读护栏 | `HUAWEICLOUD_MCP_READ_ONLY=true` 时调 `reboot_pg_instance` | 返回 `MCP_READ_ONLY` 拦截信封 |

## 3. 第二级：功能验证（对应规范「功能验证」，只读 → 写）

只读：`list_pg_instances` 返回实例列表且与控制台数量/状态一致；`show_pg_instance` 关键字段（datastore/flavor/volume/ha）与控制台一致。

两段式写通路（任选一个低危操作，如 reboot 预览）：

| # | 检查 | 成功标准 |
|---|---|---|
| V2.1 | `confirm=false` 预览 | `confirmation_required` + changes + warnings + plan_id + expires_at；控制台实例无变化 |
| V2.2 | 同参 `confirm=true` + plan_id 提交 | `submitted` + job_id |
| V2.3 | `show_pg_instance_job` 轮询 | Running → Completed |
| V2.4 | 复核 | `show_pg_instance` ACTIVE 且无 action 锁 |
| V2.5 | 重放已消费 plan_id | `MCP_GUARDRAIL_BLOCKED (already used)` —— 防重放生效 |

## 4. 第三级：验收五连验（发版/合入前）

对 13.4 检查清单逐项核对，映射到本技能形态：

| 规范五连验 | 本技能落地 |
|---|---|
| 命令格式验证 | 工具命名 `动词_对象`、74 工具逐一带 `@guard(risk=...)` 声明（对 MCP 型技能替代 hcloud 命令格式检查） |
| 参数格式验证 | 写工具统一 `confirm: bool` + `plan_id` 契约；密码一律 `password_ref`（request_ref 别名），明文不入参 |
| 输出格式验证 | 统一 JSON 信封（page_result / confirmation_required / submitted / 错误信封含 request_id + hint） |
| 错误处理验证 | 凭证缺失、实例不存在（MCP_NOT_FOUND）、实例忙（DBS.201015）、权限不足（403 DBS.280015）、只读拦截均有明确信封与 hint |
| 安全验证 | grep 无 AK/SK 硬编码；审计 JSONL 中 params 字段脱敏；plan_id 单次消费（重放/嫁接/过期均 blocked） |

## 5. 测试矩阵引用

完整现网用例（每条含操作 + 验收标准 + 实测状态）见 MCP 工程 `server/mcp_server_rds_pg/LIVE-TESTING.md`：

- **G1-G6 机制组**：基础读写 / 两段式管线（含重放、嫁接、过期、action 锁）/ 双写开关 / 保护规则 / 审计 / 协议冒烟
- **B1-B16 业务场景组**：一场景一组，对齐设计文档 §3.1-§3.10（巡检/重启/停机/开通/密码/连接/备份/库账号/变配/监控/日志/参数/插件等）
- 执行顺序：G → 已实现 B 组 → 新交付 B 组逐组点亮

## 6. ✅/❌ 正误对比

- ✅ 写操作验证走「预览 → 确认 → 提交 → 轮询 → 复核」全链，任何一环失败即记录
- ❌ 只调一次 `confirm=true` 就认为通过（跳过预览与复核，无法发现防重放/状态机缺陷）
- ❌ 在对话/报告中回显密码或 AK/SK 做「验证」（安全验证的要点恰恰是证明它们**不出现**）
