# 项目状态契约（webapp.json）

跨会话断点续作的载体。文件：项目根 `.hwsupabase/webapp.json`（目录排除 Git）。与 rds-supabase-frontend 技能的发布记录契约（`.hwsupabase/frontend/`）同根互补：**引用不复制**——前端版本/验收/回退记录以 frontend 契约为唯一权威。加载时机：首次读写 webapp.json 前。

## 通用规则

- `schema_version` 为整数 `1`；读取时版本不符 → 停止并报告，不猜测迁移
- 时间使用 RFC 3339 UTC（如 `2026-11-10T08:00:00Z`）；sha256 为 64 位小写十六进制
- **密钥、数据库密码、云凭证、cookie、token、用户数据不入记录**；凭据只记环境变量名与注入状态
- 公共必填字段即使未知也保留，值为 `null`；不把 `null` 当作不存在或已验证
- 每次操作是新的当前操作：更新/回滚/下线不改写历史事件，只追加

## 字段表

### 顶层

| 字段 | 类型 | 规则 |
|---|---|---|
| schema_version | integer | 固定 `1` |
| project | object | 见下 |
| instance | object/null | 未进入①时为 `null` |
| backend | object/null | 未部署时为 `null` |
| frontend | object/null | 未生成时为 `null` |
| stages | object | 见下 |

### project

| 字段 | 类型 | 规则 |
|---|---|---|
| name | string | 项目名 |
| description | string/null | 一句话描述 |
| requirements_summary | string | ⓪ 确认的需求摘要（脱敏，不含凭据与用户数据） |

### instance

| 字段 | 类型 | 规则 |
|---|---|---|
| supabase_application_id | string | 管理面应用 ID |
| source | string | `created`（本流程新建）或 `selected`（① 用户选定已有应用） |
| gateway_url | string | Kong 网关地址 |
| credential_env_names | string[] | 固定 `["SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_ROLE_KEY"]` |
| credential_source | string | `devkit` 或 `protected_file` |
| region | string/null | 区域（如适用） |

### backend

| 字段 | 类型 | 规则 |
|---|---|---|
| current_batch | string/null | 当前生效批次 ID |
| deployments | object[] | 每项必含 `batch_id`、`applied_at`、`objects`（字符串数组）、`source_sha256`、`status`（`applied`/`failed`/`rolled_back`） |

### frontend

| 字段 | 类型 | 规则 |
|---|---|---|
| record_ref | string | 指向 `.hwsupabase/frontend/<env>/environment.json` |
| project_dir | string | 前端项目目录（相对项目根） |
| framework | string | 如 `react-vite-ts` |

### stages

| 字段 | 类型 | 规则 |
|---|---|---|
| last_completed_stage | string | 枚举见下 |
| updated_at | string | 本次更新时间 |
| history | object[] | 每项必含 `stage`、`status`（`passed`/`failed`/`blocked`）、`at`、`note` |

**阶段枚举**：`requirements_confirmed` → `instance_ready` → `mcp_connected` → `backend_deployed` → `frontend_built` → `hosting_published` → `launched`；另有终态 `decommissioned`（下线后）。

## 门槛产物与执行轨迹

| 产物 | 路径 | 规则 |
|---|---|---|
| ③ 规则对照表 | `.hwsupabase/gates/3-rules-checklist.md` | best-practices 规则 → init.sql 位置映射，≥5 条 `- <规则> → <位置>` 行；③ 完成前 gate `check-gate --number 3` 校验 |
| ④ SDK 契约对照表 | `.hwsupabase/gates/4-sdk-contract-checklist.md` | usage 契约点 → 代码位置映射（会话管理/RLS 语义/错误契约/env 注入/Realtime 清理），≥5 条映射行；④ 完成前 gate `check-gate --number 4` 校验 |
| 执行轨迹 | `.hwsupabase/trace.jsonl` | 每个 MCP/CLI 工具调用后即时追加一行：`{"at":<RFC3339 UTC>,"stage":<阶段枚举>,"tool":<工具名>,"intent":<一句话>,"status":"ok|fail|blocked","note":null}`；**无敏感值**；gate `check-trace` 校验格式 |

## 状态不变量

1. **阶段只前进**：`last_completed_stage` 仅在对应门槛通过后更新；断点重验失败不改写已通过阶段，只在 history 记录 `failed`
2. **失败/未知显式记录**（history.status + note），不猜测、不静默跳过
3. **断点续作**从 `last_completed_stage` 的下一阶段重入，且必须重验该阶段门槛（不信任历史结论）
4. **密钥轮换**后仅更新 `credential_source` 与注入状态，仍不记录任何凭据值
5. 前端记录变化（新版本/回退）只需保持 `record_ref` 指向有效环境记录，不在本文件复制其字段
