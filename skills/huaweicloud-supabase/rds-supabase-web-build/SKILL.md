---
name: rds-supabase-web-build
description: 'RDS Supabase 全栈开发编排技能：AI Agent 通过自然语言创建并托管 Web 应用网站的端到端工作流——前端代码生成、后端 init.sql（DDL/GRANT/RLS/RPC）生成与部署、前端静态资源 OBS+CDN 全托管、端到端上线与生命周期管理（更新/回滚/下线）。Use when：创建 Web 网站、搭建 AI 应用、全栈应用从零到上线、已有 RDS Supabase 应用的迭代更新与托管维护。编排管理面与数据面两台 MCP（均由工作流步骤动态安装：管理面→步骤三、数据面→步骤四）及 rds-supabase-mgr-mcp / rds-supabase-mcp / rds-supabase-usage / rds-supabase-frontend / rds-supabase-postgres-best-practices 五个专项技能。v1 后端边界为数据层；复杂业务逻辑（支付/第三方调用/长任务）不在 v1 范围，SSR 后端部署不支持。'
license: MIT
metadata:
  version: "0.6.3"
---

# RDS Supabase 全栈开发编排（web-build）

## 概述

RDS Supabase 全栈开发的**顶层编排技能**：用户以单句自然语言需求（如"创建一个网站"）触发，AI Agent 完成前端与后端的代码生成、部署运行、托管上线的完整链路。本技能是厚工作流编排者——内置步骤状态机、通过条件、失败处置与断点续作；各环节深度内容由专项技能承载，本技能仅执行路由，不复制内容。

双工作流总图：

```
【首次创建流水线】（每步骤设有通过条件；未满足不得推进）
 步骤一 环境检查与配置 → 步骤二 需求澄清 → 步骤三 资源准备 → 步骤四 数据面接入
                ↳ 环境四项：凭据 · Region · RDS/OBS 接入点 · PROJECT_ID（缺失显式提醒用户设置）
 步骤五 后端生成部署 → 步骤六 前端生成 → 步骤七 构建与托管 → 步骤八 端到端上线
                ↳ 步骤三动态启动管理面 MCP（实例/EIP/安全组/SSL/密钥）+ OBS 租户桶
                ↳ 步骤四动态安装数据面 MCP（install.md）
 步骤七↻ 回调回路：域名确定 → 管理面配置 site_url/redirect_uris → 前端重建

【生命周期循环】（独立工作流）
 更新（增量 init.sql → 重走步骤五与步骤八）｜回滚（前端版本回退 + DB 批次管理）｜下线（清理清单）｜密钥轮换
```

双平面与双轨：

- **管理面**：`mcp_server_rds_supabase_mgr`（29 工具）——RDS Supabase 实例全托管生命周期（创建/配置/安全访问/删除）；**步骤三动态启动**，不随技能安装装载
- **数据面**：`mcp_server_rds_supabase`（38 工具）——init.sql 执行、结构查询、RLS/advisors；**步骤四动态安装**（实例凭据就绪后）
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
| 环境检查与配置（步骤一：Region / RDS·OBS 接入点 / PROJECT_ID / 凭据） | web-build 自身 + 管理面 `diagnostics discover` |
| 实例创建/配置（EIP/安全组/SSL）/密钥交付/删除 | rds-supabase-mgr-mcp 技能 + 管理面 MCP |
| 数据面 MCP 动态安装 | rds-supabase-mcp 技能 references/install.md |
| init.sql 质量规则（步骤五强制门） | rds-supabase-postgres-best-practices 技能 |
| 前端 supabase-js SDK 用法（步骤六强制门；步骤五消费视角） | rds-supabase-usage 技能 |
| 前端构建/OBS 发布/CDN/版本回退 | rds-supabase-frontend 技能 |
| init.sql 五步部署/单工具数据操作 | rds-supabase-mcp 技能 |
| SSR 后端部署 | 不支持（静态导出为边界，继承 frontend 技能策略） |
| 复杂业务逻辑（支付/第三方调用/长任务） | v1 边界外（FunctionGraph 路由留待 v2） |

## 前置条件

1. 技能包（六技能）已按 [README](README.md)/[INSTALL.md](INSTALL.md) 安装——安装阶段不含 MCP 与凭据
2. uv（含 uvx）可用——步骤三/四动态安装 MCP 所需，步骤一环境检查核对，缺失提醒用户安装
3. 步骤一执行环境检查与配置：凭据（devkit 登录态或 AK/SK）、Region（局点）、RDS 与 OBS 接入点、`HUAWEICLOUD_PROJECT_ID` 须已配置或可解析；**无法获取的项必须以缺失清单显式提醒用户设置**，不得猜测或跳过
4. 云侧付费资源（实例/OBS 桶/CDN）创建前须用户显式确认（费用预估在步骤二输出）

## 工作流（步骤一–八 分步执行）

**步骤状态机**（断点续作依据，记录于 `.hwsupabase/webapp.json` 的 `last_completed_stage`）：

```
environment_ready → requirements_confirmed → instance_ready → mcp_connected
                  → backend_deployed → frontend_built → hosting_published → launched
```

每步固定节奏：**步骤声明 → 编号动作 → 写 webapp.json → gate PASS → 步骤报告**。各步的完整 playbook（输入/输出断言/工具白名单/黄金路径/失败处置）见 references/workflow-stages.md 对应小节。

### 步骤一 · 环境检查与配置 → 断点 `environment_ready`

1. 凭据检查：devkit 登录态或 AK/SK（或服务 Token）；缺失 → 提醒用户设置
2. **uv（含 uvx）可用**——步骤三/四动态安装 MCP 的前提；缺失 → 提醒用户安装（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
3. **Region（局点）确认**：`HUAWEICLOUD_REGION` 已选择——OBS 接入点推导与桶区域的前提；缺失 → **显式提醒用户设置**
4. **RDS 接入点**：`SUPABASE_RDS_ENDPOINT` 已配置 → 采用；未配置且凭据就绪 → `diagnostics discover` 解析并经用户勾选；**无法解析 → 显式提醒用户设置**
5. **OBS 接入点**：按 Region 推导（`obs.<region>.myhuaweicloud.com`，KooCLI/SDK 自动解析）；**无法推导 → 显式提醒用户设置**
6. **PROJECT_ID**：已配置 → 采用；未配置 → discover 勾选；**无法获取 → 显式提醒用户设置**
7. 缺失项汇总为清单提醒用户逐项设置，**不得猜测、不得跳过、不得以默认值代替**；全部就绪 → 写 webapp.json（`environment_ready`）→ gate PASS

### 步骤二 · 需求澄清 → 断点 `requirements_confirmed`

1. 澄清清单逐项确认：页面清单、数据模型、认证需求、AI 能力（pgvector 检索/Realtime/文件上传为可选扩展）
2. 边界外识别（复杂业务逻辑→v2；SSR 不支持）+ 费用预估清单 → 用户确认
3. 写 webapp.json（requirements_summary）→ gate PASS

### 步骤三 · 资源准备 → 断点 `instance_ready`

1. 复核步骤一环境配置（凭据 / Region / RDS·OBS 接入点 / PROJECT_ID）仍就绪；发现缺项 → 返回步骤一补齐
2. **动态启动管理面 MCP**（已连接则跳过）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板（推荐）
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   ```

   env：`SUPABASE_RDS_ENDPOINT` / `HUAWEICLOUD_PROJECT_ID` / 凭据（devkit 优先；或 `diagnostics discover` 勾选；或半自动方案：配置模板含占位符，由用户填入实际值）
3. 实例**先问新建/已有**：已有 → `list_supabase_applications` 列表勾选 + 状态核验；新建 → 创建（仅 Single）+ 配置 EIP/安全组 8443/SSL
4. **凭据获取（两条路径均必须执行，不得遗漏）**：网关 URL + Anon/Service Role Key → 受保护文件（步骤四安装所必需）
5. OBS 租户桶（frontend 技能引导）→ 写 webapp.json instance 段 → gate PASS

### 步骤四 · 数据面接入 → 断点 `mcp_connected`

1. **动态安装数据面 MCP**（实例凭据就绪后）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   ```

   env：`SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`（agent 生成含占位符的配置模板 → 用户从受保护文件复制实际值填入 → 客户端重载）
2. 验证：`get_project_url` == 网关地址 + `list_tables` 应答 → 写 webapp.json → gate PASS

### 步骤五 · 后端生成部署 → 断点 `backend_deployed`

1. **【强制门】** 读 best-practices（逐条对照）+ usage 客户端消费视角
2. 生成 init.sql + **规则对照表** `gates/3-rules-checklist.md`（gate 校验）
3. 五步部署：预检 → 审查 → `execute_sql` 单一事务 → 授权（`NOTIFY pgrst, 'reload schema'`）→ 查询确认
4. 验证：结构确认 + RLS 生效 + advisors 无新增 + REST 200 且 anon 可见性符合设计 → 写 webapp.json（含 `exposed` 对外表清单）→ gate `--verify` PASS（机器验真）

### 步骤六 · 前端生成 → 断点 `frontend_built`

1. **【强制门】** 读 usage（SDK 正确用法，避免运行时报错）
2. 生成源码（默认 React+Vite+TS + supabase-js；仅 anon key 进产物）+ **SDK 契约对照表** `gates/4-sdk-contract-checklist.md`（gate 校验）
3. `npm run build` + 本地冒烟（首页渲染 / 1 条 RLS 查询 / 1 次 auth 流）→ 写 webapp.json → gate PASS

### 步骤七 · 构建与托管 → 断点 `hosting_published`

1. frontend 技能：build → 上传步骤三预建桶 → CDN 刷新 → 版本记录
2. **步骤七↻ 回调回路**：域名确定 → `update_supabase_auth_config` 配 site_url/redirect_uris（差异确认）→ 前端按最终地址**重建再发布**
3. 验证：frontend checks 全必需项 passed + stable_url HTTPS → 写 webapp.json → gate PASS

### 步骤八 · 端到端上线 → 断点 `launched`

1. 三层验证（launch-checklist）：后端项 / 前端项 / 连通项（站点渲染、API 可见性、**多用户隔离抽检**、auth 回调）
2. 上线报告（三级交付语义）→ 写 webapp.json → gate `--verify` PASS → 交付

**断点续作**：会话开始先读 webapp.json → 从 `last_completed_stage` 的下一步骤重入，并**重验该步骤通过条件**（不信任历史结论）。

**生命周期循环**（更新/回滚/下线/密钥轮换）：见 references/lifecycle.md。

## 执行纪律（稳定性硬约束）

以下为硬性约束，将流程的可靠执行从依赖模型自觉转变为机制核验与用户确认；违反任一条即视为该步骤失败。

1. **步骤声明**（每步骤开始时必须输出，固定格式）：

   ```
   ┌─ 步骤五 后端生成部署（前一态 mcp_connected）
   │ 允许：best-practices 对照、init.sql 生成、execute_sql 部署
   │ 禁止：前端代码、OBS 操作、跳过对照表
   └─ 完成断言：advisors 无新增 + REST 200（详细断言见 workflow-stages.md）
   ```

2. **单次回复推进单一步骤**：一次用户交互最多推进一个步骤（通过条件全过且下一步骤无用户决策点除外）
3. **等待协议**：>30s 的长操作按固定节奏轮询（job 每 30 秒、上限 20 次）；等待期间禁止发起无关操作
4. **连续失败中止规则**：同一动作连续失败 2 次 → 强制中止并向用户报告，**禁止第三次盲目重试**
5. **工具白名单**：每步骤允许/禁止集合见 workflow-stages.md；越界须先获用户同意并记 trace
6. **gate 机械核验**：步骤完成前运行本技能 `scripts/webapp-gate.py`（`check-stage --stage <标记>`；步骤五、步骤六另跑 `check-gate --number 3|4`），**PASS 才能输出步骤报告与推进**；FAIL 按缺项整改后重跑。**步骤五与步骤八的 `check-stage` 必须加 `--verify`（步骤五另加 `--mcp-command <数据面启动命令>`）**：云上事实（REST 可达/对外表 anon 可见性/RLS/advisors）由 gate 直连机器核验，不采信 agent 自报
7. **trace**：每个 MCP/CLI 工具调用后追加 `.hwsupabase/trace.jsonl` 一行（无敏感值；格式见 project-state.md）；工具调用须在该步骤白名单内（`check-whitelist` 审计，越界即违规）
8. **进度看板**：技能触发后第一动作——创建八项待办（步骤一~八，宿主待办列表联动）**并在聊天中输出完整步骤总览表**；步骤推进/受阻时两轨同步更新；重入会话时依据 webapp.json 重建

## 可用工具

| 平面 | MCP | 关键能力 |
|---|---|---|
| 管理面 | mcp_server_rds_supabase_mgr（29 工具） | 实例创建/配置（EIP/安全组/SSL）、ApiKey 交付、`update_supabase_auth_config`（回调配置）、删除；两阶段确认 + 执行账本 |
| 数据面 | mcp_server_rds_supabase（38 工具） | `execute_sql`（单一事务，五步部署执行者）、结构查询、RLS/advisors、用户管理；只读拦截/审计脱敏 |

两台 MCP **均不随技能安装装载**——场景触发技能后，由步骤三（管理面）与步骤四（数据面）在流程内自动从本仓动态安装（完整命令内联于 workflow-stages.md 对应步骤，进入时读取）。人类可读的安装指南与来源表见 [README.md](README.md) 与 [INSTALL.md](INSTALL.md)；完整路由矩阵见 references/routing-table.md。

## 参数确认

| 项 | 确认规则 |
|---|---|
| 步骤二 需求摘要与数据模型 | 用户逐项确认后才进入步骤三；模糊表述不放大授权 |
| 付费资源创建（实例/桶/CDN） | 费用预估清单展示 + 用户显式确认（管理面两阶段确认作为最终保障） |
| init.sql（步骤五产出） | best-practices 四项审查通过；破坏性语句逐条人工确认 |
| 凭据 | agent 永不接触明文；只处理 env 名与注入状态；连通性以工具调用结果证明 |
| 回调配置（步骤七↻） | 展示 site_url/redirect_uris 差异后确认 |

## 输出格式

- **进度看板**（全程维护，双轨呈现）：
  - **宿主待办联动**：触发后第一动作创建八项待办（对应步骤一~八）；进入步骤置"进行中"、gate PASS 置"已完成"、失败置"受阻"
  - **聊天内步骤总览**（强制展示，不依赖宿主待办工具是否可见）：首条回复即输出下方全表；此后**每次步骤报告头部完整重发**（状态刷新）；状态标记：⏳ 待办 / 🔄 进行中 / ✅ 已完成 / ⛔ 受阻；重入会话时依据 webapp.json 重建双轨看板

  ```
  【项目步骤总览】
  | # | 步骤 | 通过断点 | 状态 |
  |---|---|---|---|
  | 一 | 环境检查与配置 | environment_ready | 🔄 进行中 |
  | 二 | 需求澄清 | requirements_confirmed | ⏳ 待办 |
  | 三 | 资源准备 | instance_ready | ⏳ 待办 |
  | 四 | 数据面接入 | mcp_connected | ⏳ 待办 |
  | 五 | 后端生成部署 | backend_deployed | ⏳ 待办 |
  | 六 | 前端生成 | frontend_built | ⏳ 待办 |
  | 七 | 构建与托管 | hosting_published | ⏳ 待办 |
  | 八 | 端到端上线 | launched | ⏳ 待办 |
  ```
- **步骤声明**（每步骤第一条输出）：步骤号、前一态、允许/禁止动作、完成断言（格式见执行纪律）
- **对接卡片**（需要用户配置或输入时，以表格直观呈现，便于高效对接）：

  ```
  【环境检查与配置】
  | 检查项 | 状态 | 获取方式 |
  |---|---|---|
  | 凭据（devkit/AK/SK） | ✅ devkit 已登录 | — |
  | uv（含 uvx） | ✅ 0.7.18 | — |
  | Region（局点） | ❌ 未配置 | 回复局点，如 cn-north-4 |
  | RDS 接入点 | ⏳ 待推导 | discover 自动 / 需你指定 |
  | OBS 接入点 | ⏳ 按 Region 推导 | 自动 |
  | PROJECT_ID | ❌ 未配置 | discover 勾选 / 控制台查询 |
  ```

- **节点快讯**（关键动作前后各一行）：`动作 · 对象 · 结果摘要`（如"部署 init.sql · 批次 b1 · 12 对象 applied"）；长操作（实例创建/构建/部署/上传）开始与完成各发一条
- **步骤报告**（每步骤完成时）：先更新进度看板（聊天内**完整重发步骤总览表**：本步置 ✅、下一步骤置 🔄），再输出报告——目标、执行动作、通过条件验证结果（**引用 gate verdict**）、下一步骤预告 + 需要用户准备什么
- **上线报告**（步骤八）：三级交付语义（本地已验证/环境已准备/线上验收通过）+ stable_url + 前端版本记录引用；格式见 references/launch-checklist.md
- **失败/断点报告**：当前步骤、失败原因（含连续失败中止规则触发）、已恢复/待人工项、webapp.json 状态

## 验证方法

- 每步骤通过条件即验证点（见工作流表与 workflow-stages.md）
- 步骤八 上线通过条件 = 三层组合（后端项/前端项/连通项），完整清单见 references/launch-checklist.md
- 上线后复查：webapp.json 标记 launched 且 stable_url 可访问

## 注意事项

- **凭据红线**：密钥永不写入 webapp.json/会话内容/工具返回；agent 不读取交付文件；devkit 注入优先、半自动备选路径；anon key 进入前端产物属预期，Service Role Key 绝不进入
- **MCP 安装来源锁定**：两台 MCP 服务器只从**本仓**安装（uvx git 模板 `git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=...`，或本地 `uv run --directory server/... <入口脚本>`）；禁止从 PyPI/第三方仓库搜索安装——存在同名第三方 "supabase" MCP 包，会导致连接到完全错误的服务器
- **配置完备性检查**（步骤三第一动作）：管理面需凭据 + `HUAWEICLOUD_PROJECT_ID` + `SUPABASE_RDS_ENDPOINT`；frontend/OBS 需 AK/SK + `HUAWEICLOUD_REGION`。缺失项以清单**以清单形式提示用户填写**（不猜测不跳过）；endpoint 无法推导（discover 失败/非标准区域）→ 用户显式指定
- **边界外处置**：复杂业务逻辑（支付/第三方调用/长任务）超出 v1 数据层边界——明确告知用户并停止，不擅自以 RPC 模拟
- 文件上传（Storage）v1 默认不含：步骤二 识别并说明（可选扩展路径：管理面 `update_supabase_storage` 配 OBS 凭据）
- v1 单环境（webapp.json 字段预留多环境扩展）
- 管理面操作遵循其两阶段确认与执行账本；未知结果不重放、不删账本
- 步骤通过条件未满足不得推进；强制门（步骤五步骤六）不可跳过

## 文档加载策略

本技能共 6 份文档（SKILL.md + 5 references），**渐进加载**：SKILL.md 随技能触发常驻（双工作流总图、状态机、通过条件与红线足以推进到任一步骤入口）；references 按时机加载，未进入对应步骤或操作**不预读**。

| 时机 | 加载 | 目的 |
|---|---|---|
| 会话开始（技能触发后第一动作） | 项目根 `.hwsupabase/webapp.json`（若存在） | 判断断点：从 `last_completed_stage` 下一步骤重入 |
| 首次读写 webapp.json 前 | references/project-state.md | 契约字段与不变量 |
| 进入任一步骤（步骤一–八）执行前 | references/workflow-stages.md 对应步骤小节 | 该步骤输入/动作/通过条件/失败处置 |
| 任务归属技能/文档不明时 | references/routing-table.md | 正向/负向路由矩阵 |
| 步骤五 生成 init.sql 前 | 【强制门】rds-supabase-postgres-best-practices 技能（+ init-sql-guide） | 质量规则逐条对照 |
| 步骤六 生成前端前 | 【强制门】rds-supabase-usage 技能 | SDK 正确用法，避免运行时报错 |
| 步骤八 上线验证前 | references/launch-checklist.md | 三层清单与上线报告格式 |
| 每步骤完成前 | scripts/webapp-gate.py（check-stage；步骤五、步骤六另跑 check-gate） | 🤖 断言机械核验，PASS 才算完成 |
| launched 之后的更新/回滚/下线/密钥轮换 | references/lifecycle.md | 生命周期工作流 |

一次会话的典型加载量：SKILL.md + project-state.md + workflow-stages.md 当前步骤小节 + 步骤强制门技能（如有）。routing-table.md 仅在路由不明时查询；不在早期步骤预加载 launch-checklist.md 与 lifecycle.md。

## 参考文档

- references/workflow-stages.md（步骤一–八 步骤 playbook；进入对应步骤前读）
- references/lifecycle.md（更新/回滚/下线/密钥轮换；launched 后读）
- references/project-state.md（webapp.json 契约；首次读写前读）
- references/routing-table.md（跨技能/MCP 路由矩阵；路由不明时查）
- references/launch-checklist.md（端到端上线清单；步骤八 验证前读）
- scripts/webapp-gate.py（步骤通过条件机械核验；每步骤完成前运行）
