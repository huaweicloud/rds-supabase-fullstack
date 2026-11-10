---
name: rds-supabase-web-build
description: 'RDS Supabase 全栈开发编排技能：AI Agent 通过自然语言创建并托管 Web 应用网站的端到端工作流——前端代码生成、后端 init.sql（DDL/GRANT/RLS/RPC）生成与部署、前端静态资源 OBS+CDN 全托管、端到端上线与生命周期管理（更新/回滚/下线）。Use when：创建 Web 网站、搭建 AI 应用、全栈应用从零到上线、已有 RDS Supabase 应用的迭代更新与托管维护。编排管理面 MCP（实例生命周期）与数据面 MCP（动态安装）及 rds-supabase-mgr-mcp / rds-supabase-mcp / rds-supabase-usage / rds-supabase-frontend / rds-supabase-postgres-best-practices 五个专项技能。v1 后端边界为数据层；复杂业务逻辑（支付/第三方调用/长任务）不在 v1 范围，SSR 后端部署不支持。'
license: MIT
metadata:
  version: "0.3.3"
---

# RDS Supabase 全栈开发编排（web-build）

## 概述

RDS Supabase 全栈开发的**顶层编排技能**：用户以单句自然语言需求（如"创建一个网站"）触发，AI Agent 完成前端与后端的代码生成、部署运行、托管上线的完整链路。本技能是厚工作流编排者——内置步骤状态机、通过条件、失败处置与断点续作；各环节深度内容由专项技能承载，本技能仅执行路由，不复制内容。

双工作流总图：

```
【首次创建流水线】（每步骤设有通过条件；未满足不得推进）
 步骤一 需求澄清 → 步骤二 资源准备 → 步骤三 数据面接入 → 步骤四 后端生成部署 → 步骤五 前端生成 → 步骤六 构建与托管 → 步骤七 端到端上线
                ↳ 管理面 MCP（实例/EIP/安全组/SSL/密钥）+ OBS 租户桶
                ↳ install.md 动态安装数据面 MCP
 步骤六↻ 回调回路：域名确定 → 管理面配置 site_url/redirect_uris → 前端重建

【生命周期循环】（独立工作流）
 更新（增量 init.sql → 重走步骤四步骤七）｜回滚（前端版本回退 + DB 批次管理）｜下线（清理清单）｜密钥轮换
```

双平面与双轨：

- **管理面**：`mcp_server_rds_supabase_mgr`（29 工具）——RDS Supabase 实例全托管生命周期（创建/配置/安全访问/删除）
- **数据面**：`mcp_server_rds_supabase`（38 工具）——init.sql 执行、结构查询、RLS/advisors
- **后端轨**：产出 init.sql（DDL/GRANT/RLS/RPC/种子），运行于 RDS Supabase（PostgREST/GoTrue）
- **前端轨**：产出静态站点（默认 React+Vite+TS + supabase-js），托管于 OBS+CDN

## 适用范围

**触发条件**（满足任一即启用）：

1. 创建 Web 网站 / 搭建 AI 应用（从零到上线的全栈需求）
2. 全栈应用需要完整走"前端 + 后端 + 托管 + 上线"链路
3. 已有 RDS Supabase 应用的迭代更新、回滚、下线

**边界**（编排者不做细节，路由到位）：

| 任务 | 归属 |
|---|---|
| 实例创建/配置（EIP/安全组/SSL）/密钥交付/删除 | rds-supabase-mgr-mcp 技能 + 管理面 MCP |
| 数据面 MCP 动态安装 | rds-supabase-mcp 技能 references/install.md |
| init.sql 质量规则（步骤四强制门） | rds-supabase-postgres-best-practices 技能 |
| 前端 supabase-js SDK 用法（步骤五强制门；步骤四消费视角） | rds-supabase-usage 技能 |
| 前端构建/OBS 发布/CDN/版本回退 | rds-supabase-frontend 技能 |
| init.sql 五步部署/单工具数据操作 | rds-supabase-mcp 技能 |
| SSR 后端部署 | 不支持（静态导出为边界，继承 frontend 技能策略） |
| 复杂业务逻辑（支付/第三方调用/长任务） | v1 边界外（FunctionGraph 路由留待 v2） |

## 前置条件

1. uv（含 uvx）已安装；MCP 客户端（Claude Code 等）可用
2. 步骤二 起点：devkit 已在用户登录时初始化管理面 MCP 与凭据；或可经本仓 uvx 模板动态启动管理面 MCP（凭据由用户提供或经受保护文件交付）；frontend/OBS 侧需 AK/SK 与 `HUAWEICLOUD_REGION`（步骤二 逐一检查，缺失由用户补填）
3. 云侧付费资源（实例/OBS 桶/CDN）创建前须用户显式确认（费用预估在步骤一输出）

## 工作流（步骤一–七 分步执行）

**步骤状态机**（断点续作依据，记录于 `.hwsupabase/webapp.json` 的 `last_completed_stage`）：

```
requirements_confirmed → instance_ready → mcp_connected → backend_deployed
                      → frontend_built → hosting_published → launched
```

每步固定节奏：**步骤声明 → 编号动作 → 写 webapp.json → gate PASS → 步骤报告**。各步的完整 playbook（输入/输出断言/工具白名单/黄金路径/失败处置）见 references/workflow-stages.md 对应小节。

### 步骤一 · 需求澄清 → 断点 `requirements_confirmed`

1. 澄清清单逐项确认：页面清单、数据模型、认证需求、AI 能力（pgvector 检索/Realtime/文件上传为可选扩展）
2. 边界外识别（复杂业务逻辑→v2；SSR 不支持）+ 费用预估清单 → 用户确认
3. 写 webapp.json（requirements_summary）→ gate PASS

### 步骤二 · 资源准备 → 断点 `instance_ready`

1. **配置完备性检查**：管理面（凭据 / `HUAWEICLOUD_PROJECT_ID` / `SUPABASE_RDS_ENDPOINT`）+ frontend/OBS（AK/SK + `HUAWEICLOUD_REGION`）——缺项**列清单提示用户填写**；endpoint 无法推导 → 用户显式指定
2. **动态启动管理面 MCP**（已连接则跳过）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板（推荐）
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   ```

   env：`SUPABASE_RDS_ENDPOINT` / `HUAWEICLOUD_PROJECT_ID` / 凭据（devkit 优先；或 `diagnostics discover` 勾选；或半自动方案：配置模板含占位符，由用户填入实际值）
3. 实例**先问新建/已有**：已有 → `list_supabase_applications` 列表勾选 + 状态核验；新建 → 创建（仅 Single）+ 配置 EIP/安全组 8443/SSL
4. **凭据获取（两条路径均必须执行，不得遗漏）**：网关 URL + Anon/Service Role Key → 受保护文件（步骤三安装所必需）
5. OBS 租户桶（frontend 技能引导）→ 写 webapp.json instance 段 → gate PASS

### 步骤三 · 数据面接入 → 断点 `mcp_connected`

1. **动态安装数据面 MCP**（实例凭据就绪后）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   ```

   env：`SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`（agent 生成含占位符的配置模板 → 用户从受保护文件复制实际值填入 → 客户端重载）
2. 验证：`get_project_url` == 网关地址 + `list_tables` 应答 → 写 webapp.json → gate PASS

### 步骤四 · 后端生成部署 → 断点 `backend_deployed`

1. **【强制门】** 读 best-practices（逐条对照）+ usage 客户端消费视角
2. 生成 init.sql + **规则对照表** `gates/3-rules-checklist.md`（gate 校验）
3. 五步部署：预检 → 审查 → `execute_sql` 单一事务 → 授权（`NOTIFY pgrst, 'reload schema'`）→ 查询确认
4. 验证：结构确认 + RLS 生效 + advisors 无新增 + REST 200 且 anon 可见性符合设计 → 写 webapp.json → gate PASS

### 步骤五 · 前端生成 → 断点 `frontend_built`

1. **【强制门】** 读 usage（SDK 正确用法，避免运行时报错）
2. 生成源码（默认 React+Vite+TS + supabase-js；仅 anon key 进产物）+ **SDK 契约对照表** `gates/4-sdk-contract-checklist.md`（gate 校验）
3. `npm run build` + 本地冒烟（首页渲染 / 1 条 RLS 查询 / 1 次 auth 流）→ 写 webapp.json → gate PASS

### 步骤六 · 构建与托管 → 断点 `hosting_published`

1. frontend 技能：build → 上传步骤二预建桶 → CDN 刷新 → 版本记录
2. **步骤六↻ 回调回路**：域名确定 → `update_supabase_auth_config` 配 site_url/redirect_uris（差异确认）→ 前端按最终地址**重建再发布**
3. 验证：frontend checks 全必需项 passed + stable_url HTTPS → 写 webapp.json → gate PASS

### 步骤七 · 端到端上线 → 断点 `launched`

1. 三层验证（launch-checklist）：后端项 / 前端项 / 连通项（站点渲染、API 可见性、**多用户隔离抽检**、auth 回调）
2. 上线报告（三级交付语义）→ 写 webapp.json → gate PASS → 交付

**断点续作**：会话开始先读 webapp.json → 从 `last_completed_stage` 的下一步骤重入，并**重验该步骤通过条件**（不信任历史结论）。

**生命周期循环**（更新/回滚/下线/密钥轮换）：见 references/lifecycle.md。

## 执行纪律（稳定性硬约束）

以下为硬性约束，将流程的可靠执行从依赖模型自觉转变为机制核验与用户确认；违反任一条即视为该步骤失败。

1. **步骤声明**（每步骤开始时必须输出，固定格式）：

   ```
   ┌─ 步骤四 后端生成部署（前一态 mcp_connected）
   │ 允许：best-practices 对照、init.sql 生成、execute_sql 部署
   │ 禁止：前端代码、OBS 操作、跳过对照表
   └─ 完成断言：advisors 无新增 + REST 200（详细断言见 workflow-stages.md）
   ```

2. **单次回复推进单一步骤**：一次用户交互最多推进一个步骤（通过条件全过且下一步骤无用户决策点除外）
3. **等待协议**：>30s 的长操作按固定节奏轮询（job 每 30 秒、上限 20 次）；等待期间禁止发起无关操作
4. **连续失败中止规则**：同一动作连续失败 2 次 → 强制中止并向用户报告，**禁止第三次盲目重试**
5. **工具白名单**：每步骤允许/禁止集合见 workflow-stages.md；越界须先获用户同意并记 trace
6. **gate 机械核验**：步骤完成前运行本技能 `scripts/webapp-gate.py`（`check-stage --stage <标记>`；步骤四、步骤五另跑 `check-gate --number 3|4`），**PASS 才能输出步骤报告与推进**；FAIL 按缺项整改后重跑
7. **trace**：每个 MCP/CLI 工具调用后追加 `.hwsupabase/trace.jsonl` 一行（无敏感值；格式见 project-state.md）

## 可用工具

| 平面 | MCP | 关键能力 |
|---|---|---|
| 管理面 | mcp_server_rds_supabase_mgr（29 工具） | 实例创建/配置（EIP/安全组/SSL）、ApiKey 交付、`update_supabase_auth_config`（回调配置）、删除；两阶段确认 + 执行账本 |
| 数据面 | mcp_server_rds_supabase（38 工具） | `execute_sql`（单一事务，五步部署执行者）、结构查询、RLS/advisors、用户管理；只读拦截/审计脱敏 |

MCP 动态安装的**唯一来源与完整 URL 命令内联于 workflow-stages.md 步骤二步骤三**（进入步骤执行时读取）；人类可读的安装指南与来源表见 [README.md](README.md) 与 [INSTALL.md](INSTALL.md)。完整路由矩阵见 references/routing-table.md。

## 参数确认

| 项 | 确认规则 |
|---|---|
| 步骤一 需求摘要与数据模型 | 用户逐项确认后才进入步骤二；模糊表述不放大授权 |
| 付费资源创建（实例/桶/CDN） | 费用预估清单展示 + 用户显式确认（管理面两阶段确认作为最终保障） |
| init.sql（步骤四 产出） | best-practices 四项审查通过；破坏性语句逐条人工确认 |
| 凭据 | agent 永不接触明文；只处理 env 名与注入状态；连通性以工具调用结果证明 |
| 回调配置（步骤六↻） | 展示 site_url/redirect_uris 差异后确认 |

## 输出格式

- **步骤声明**（每步骤第一条输出）：步骤号、前一态、允许/禁止动作、完成断言（格式见执行纪律）
- **步骤报告**（每步骤完成时）：目标、执行动作、通过条件验证结果（**引用 gate verdict**）、下一步骤预告 + 需要用户准备什么
- **上线报告**（步骤七）：三级交付语义（本地已验证/环境已准备/线上验收通过）+ stable_url + 前端版本记录引用；格式见 references/launch-checklist.md
- **失败/断点报告**：当前步骤、失败原因（含连续失败中止规则触发）、已恢复/待人工项、webapp.json 状态

## 验证方法

- 每步骤通过条件即验证点（见工作流表与 workflow-stages.md）
- 步骤七 上线通过条件 = 三层组合（后端项/前端项/连通项），完整清单见 references/launch-checklist.md
- 上线后复查：webapp.json 标记 launched 且 stable_url 可访问

## 注意事项

- **凭据红线**：密钥永不写入 webapp.json/会话内容/工具返回；agent 不读取交付文件；devkit 注入优先、半自动备选路径；anon key 进入前端产物属预期，Service Role Key 绝不进入
- **MCP 安装来源锁定**：两台 MCP 服务器只从**本仓**安装（uvx git 模板 `git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=...`，或本地 `uv run --directory server/... <入口脚本>`）；禁止从 PyPI/第三方仓库搜索安装——存在同名第三方 "supabase" MCP 包，会导致连接到完全错误的服务器
- **配置完备性检查**（步骤二 第一动作）：管理面需凭据 + `HUAWEICLOUD_PROJECT_ID` + `SUPABASE_RDS_ENDPOINT`；frontend/OBS 需 AK/SK + `HUAWEICLOUD_REGION`。缺失项以清单**以清单形式提示用户填写**（不猜测不跳过）；endpoint 无法推导（discover 失败/非标准区域）→ 用户显式指定
- **边界外处置**：复杂业务逻辑（支付/第三方调用/长任务）超出 v1 数据层边界——明确告知用户并停止，不擅自以 RPC 模拟
- 文件上传（Storage）v1 默认不含：步骤一 识别并说明（可选扩展路径：管理面 `update_supabase_storage` 配 OBS 凭据）
- v1 单环境（webapp.json 字段预留多环境扩展）
- 管理面操作遵循其两阶段确认与执行账本；未知结果不重放、不删账本
- 步骤通过条件未满足不得推进；强制门（步骤四步骤五）不可跳过

## 文档加载策略

本技能共 6 份文档（SKILL.md + 5 references），**渐进加载**：SKILL.md 随技能触发常驻（双工作流总图、状态机、通过条件与红线足以推进到任一步骤入口）；references 按时机加载，未进入对应步骤或操作**不预读**。

| 时机 | 加载 | 目的 |
|---|---|---|
| 会话开始（技能触发后第一动作） | 项目根 `.hwsupabase/webapp.json`（若存在） | 判断断点：从 `last_completed_stage` 下一步骤重入 |
| 首次读写 webapp.json 前 | references/project-state.md | 契约字段与不变量 |
| 进入任一步骤（步骤一–七）执行前 | references/workflow-stages.md 对应步骤小节 | 该步骤输入/动作/通过条件/失败处置 |
| 任务归属技能/文档不明时 | references/routing-table.md | 正向/负向路由矩阵 |
| 步骤四 生成 init.sql 前 | 【强制门】rds-supabase-postgres-best-practices 技能（+ init-sql-guide） | 质量规则逐条对照 |
| 步骤五 生成前端前 | 【强制门】rds-supabase-usage 技能 | SDK 正确用法，避免运行时报错 |
| 步骤七 上线验证前 | references/launch-checklist.md | 三层清单与上线报告格式 |
| 每步骤完成前 | scripts/webapp-gate.py（check-stage；步骤四、步骤五另跑 check-gate） | 🤖 断言机械核验，PASS 才算完成 |
| launched 之后的更新/回滚/下线/密钥轮换 | references/lifecycle.md | 生命周期工作流 |

一次会话的典型加载量：SKILL.md + project-state.md + workflow-stages.md 当前步骤小节 + 步骤强制门技能（如有）。routing-table.md 仅在路由不明时查询；不在早期步骤预加载 launch-checklist.md 与 lifecycle.md。

## 参考文档

- references/workflow-stages.md（步骤一–七 步骤 playbook；进入对应步骤前读）
- references/lifecycle.md（更新/回滚/下线/密钥轮换；launched 后读）
- references/project-state.md（webapp.json 契约；首次读写前读）
- references/routing-table.md（跨技能/MCP 路由矩阵；路由不明时查）
- references/launch-checklist.md（端到端上线清单；步骤七 验证前读）
- scripts/webapp-gate.py（步骤通过条件机械核验；每步骤完成前运行）
