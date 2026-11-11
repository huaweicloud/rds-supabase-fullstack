# 项目状态契约（webapp.json）

跨会话断点续作的载体。文件：项目根 `.hwsupabase/webapp.json`（目录排除 Git）。

## 凭据存放（项目级隔离）

登录态与凭据只存放于当前项目内，不影响、不污染其他项目：

| 位置 | 内容 | 约束 |
|---|---|---|
| `<项目根>/.hwsupabase/secrets/` | Key 交付文件、项目凭据 JSON | 属主本人、0600、排除 Git；agent 不读取内容 |
| `<项目根>/.hwsupabase/requests.json` | `SUPABASE_REQUESTS_FILE` 注册表（alias → output_file 绝对路径） | 注册表本身无秘密值 |
| MCP 进程 env | 三件套注入（`SUPABASE_URL` 等） | 作用域仅该 MCP 进程；不 `export` 到 shell、不写 shell profile |
| `HUAWEICLOUD_MCP_CREDENTIALS_FILE` / `HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE` | 指向项目内 0600 凭据文件 | 项目级替代个人级 `~/.config/huaweicloud/credentials.json` |

红线：禁止写入全局/系统环境变量与个人级配置（shell profile、`~/.config/huaweicloud/`、`~/.obsutilconfig`）——已有个人级文件属既有工具与其他项目，不迁移、不删除、不覆写；凭据轮换只更新本项目 secrets/ 与进程注入，其他项目无感知；`.hwsupabase/` 整目录必须列入项目 `.gitignore`。与 rds-supabase-frontend 技能的发布记录契约（`.hwsupabase/frontend/`）同根互补：**引用不复制**——前端版本/验收/回退记录以 frontend 契约为唯一权威。加载时机：首次读写 webapp.json 前。

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
| instance | object/null | 未进入步骤三时为 `null` |
| obs | object/null | 未进入步骤三时为 `null` |
| mcp | object/null | 未进入步骤三时为 `null` |
| storage | object/null | 步骤二未标记 `storage` 能力或尚未完成对接时为 `null` |
| backend | object/null | 未部署时为 `null` |
| frontend | object/null | 未生成时为 `null` |
| stages | object | 见下 |

### project

| 字段 | 类型 | 规则 |
|---|---|---|
| name | string | 项目名 |
| description | string/null | 一句话描述 |
| requirements_summary | string | 步骤二 确认的需求摘要（脱敏，不含凭据与用户数据） |
| baas_capabilities | string[] | 步骤二 提炼的 BaaS 能力需求清单（枚举 `database`/`auth`/`rpc`/`storage`/`realtime`/`vector`，非空）；含 `storage` 时步骤三必须完成 Storage 桶准备与对接（gate 校验 storage 段存在且 connected） |

### instance

| 字段 | 类型 | 规则 |
|---|---|---|
| supabase_application_id | string | 管理面应用 ID |
| source | string | `created`（本流程新建）或 `selected`（步骤三用户选定已有应用） |
| gateway_url | string | Kong 网关地址 |
| ssl_enabled | boolean | 实例是否启用 SSL——步骤三创建/选定实例后记录，`change_supabase_ssl` 变更后同步更新；`false` 时数据面经 **HTTP** 访问（非强制 HTTPS 交互），gate `--verify` 放行 http；`true` 时强制 HTTPS。**前端托管入口协议同源跟随**：`true` → stable_url 须 HTTPS，`false` → 须 HTTP（HTTPS 页面调用 HTTP 网关属混合内容，被浏览器拦截）；gate 自 hosting_published 起读 frontend record 的 stable_url 机器核验一致性 |
| credential_env_names | string[] | 固定 `["SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_ROLE_KEY"]` |
| credential_source | string | `devkit` 或 `protected_file` |
| region | string/null | 区域（如适用） |

### obs

| 字段 | 类型 | 规则 |
|---|---|---|
| bucket_name | string | 选定或新建的桶名：3–63 字符，仅小写字母、数字与连字符，以字母或数字开头与结尾 |
| source | string | `created`（本流程新建，桶名经用户确认）或 `selected`（步骤三用户自公开读候选勾选） |
| naming_basis | string/null | `created` 时必填：`app_name_slug`（应用名英文化）或 `app_name_slug_uuid`（英文化后名称冲突，追加短 uuid 后缀）；`selected` 时为 `null` |

### storage

| 字段 | 类型 | 规则 |
|---|---|---|
| bucket_name | string | Storage 对接专用私有桶名（3–63 字符规范同 obs）；**必须与前端托管桶 `obs.bucket_name` 不同**（公开读桶复用即权限越界）——gate 机器核验 |
| source | string | `created`（本流程新建私有桶）或 `selected`（用户勾选既有桶，**桶策略安全评估通过**：无公开读/匿名 GetObject/公开列举） |
| connected | boolean | 管理面 `update_supabase_storage` 对接完成；能力清单含 `storage` 时自 instance_ready 起必须为 `true`（gate 校验） |

### mcp

| 字段 | 类型 | 规则 |
|---|---|---|
| registration_scope | string | 固定 `project`——两台 MCP 只注册进当前项目的项目级 Agent 配置，其他项目不可见（用户级/系统级注册属边界溢出，禁止）；gate 校验枚举 |
| config_paths | object | 必含 `mgr`（instance_ready 起必填）与 `data`（mcp_connected 起必填），值为**项目根相对路径**（以 `.` 开头，如 `.opencode/mcp.json`）；禁止绝对路径、`~` 与 `..`——gate 机器核验，即项目级隔离的结构化保障 |

### backend

| 字段 | 类型 | 规则 |
|---|---|---|
| current_batch | string/null | 当前生效批次 ID |
| teardown_ref | string | 一键清理脚本路径（`.hwsupabase/teardown.sql`）——步骤五 与 init.sql 同源生成、随批次刷新；`backend_deployed` 起必填；gate 校验其覆盖最新批次 `objects` 全部对象 |
| deployments | object[] | 每项必含 `batch_id`、`applied_at`、`objects`（字符串数组）、`source_sha256`、`status`（`applied`/`failed`/`rolled_back`）；可含 `exposed`（字符串数组，`objects` 子集——对外暴露表，`--verify` 以 anon key 机器核验其 REST 可达） |

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

**步骤枚举**：`environment_ready` → `requirements_confirmed` → `instance_ready` → `mcp_connected` → `backend_deployed` → `frontend_built` → `local_verified` → `hosting_published` → `launched`；另有终态 `decommissioned`（下线后）。

## 通过条件产物与执行轨迹

| 产物 | 路径 | 规则 |
|---|---|---|
| 步骤五 规则对照表 | `.hwsupabase/gates/3-rules-checklist.md` | 映射行格式 `- <规则文件名 stem>：说明 → <位置>`，stem 须为 best-practices 技能 `references/` 下真实规则文件名（gate 校验真实性）；≥5 条有效映射；步骤五完成前 `check-gate --number 3` 校验 |
| 步骤六 SDK 契约对照表 | `.hwsupabase/gates/4-sdk-contract-checklist.md` | usage 契约点 → 代码位置映射（会话管理/RLS 语义/错误契约/env 注入/Realtime 清理），≥5 条映射行；步骤六 完成前 gate `check-gate --number 4` 校验 |
| 步骤七 L0 测试报告 | `.hwsupabase/gates/5-local-test-report.md` | 每用例一行，格式 `- T<编号>：<场景/用例名> → passed`（修复记录附后）；**全部 passed 才算通过**；步骤七完成前 `check-gate --number 5` 校验（≥5 条 passed、零 failed） |
| 执行轨迹 | `.hwsupabase/trace.jsonl` | 每个 MCP/CLI 工具调用后即时追加一行：`{"at":<RFC3339 UTC>,"stage":<步骤枚举>,"tool":<工具名>,"intent":<一句话>,"status":"ok|fail|blocked","note":null}`；`tool` 记 MCP 工具名或 CLI 命令名（如 `execute_sql` / `hcloud obs ls` / `npm run build`）；**无敏感值**；gate `check-trace` 校验格式；**trace 强制化**——instance_ready 起各步骤 passed 前须有该步骤 ok 记录；工具须在该步骤白名单内（`check-whitelist` 审计）；`tool` 记 MCP 工具名或 CLI 命令名（如 `execute_sql` / `hcloud obs ls` / `npm run build`）；**trace 强制化**：instance_ready 起各步骤 passed 前须有该步骤 ok 记录；工具须在步骤白名单内（`check-whitelist` 审计） |

## 状态不变量

1. **步骤只前进**：`last_completed_stage` 仅在对应通过条件通过后更新；断点重验失败不改写已通过步骤，只在 history 记录 `failed`
2. **失败/未知显式记录**（history.status + note），不猜测、不静默跳过
3. **断点续作**从 `last_completed_stage` 的下一步骤重入，且必须重验该步骤通过条件（不信任历史结论）
4. **密钥轮换**后仅更新 `credential_source` 与注入状态，仍不记录任何凭据值
5. 前端记录变化（新版本/回退）只需保持 `record_ref` 指向有效环境记录，不在本文件复制其字段
