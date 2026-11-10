# 阶段 Playbook（⓪–⑥）

首次创建流水线的逐阶段执行规范。每阶段包含：目的、动作（含路由）、通过门槛、失败处置、断点标记。断点续作统一规则：会话开始先读 `.hwsupabase/webapp.json`，从 `last_completed_stage` 的下一阶段重入，并**重验该阶段门槛**——不信任历史结论。加载时机：进入对应阶段执行前（见 SKILL.md 文档加载策略）。

## ⓪ 需求澄清

**目的**：把用户一句话转化为可执行的需求摘要与数据模型草案。

**动作**：

1. 澄清清单（逐项与用户确认）：
   - 网站类型与页面清单（落地页/多页应用/仪表盘/对话式 AI 应用）
   - 数据模型草案（实体、关系、对外暴露的表）
   - 认证需求（是否登录、匿名只读、角色划分）
   - AI 能力识别：pgvector 语义检索 → ③ 生成向量列 + 索引 + 相似度 RPC；Realtime 订阅 → ④ 实时 UI；文件上传 → v1 默认不含（见边界外）
2. 边界外识别（明确告知用户，不擅自模拟）：复杂业务逻辑（支付交易/第三方接口调用/长任务）超出 v1 数据层边界，FunctionGraph 路由留待 v2；SSR 后端不支持（静态导出为边界）
3. 费用预估清单：RDS Supabase 实例（规格/时长）、OBS 桶与存储量、CDN 流量、域名/证书——展示后由用户确认
4. 需求摘要写入 webapp.json（`project.requirements_summary`，脱敏）

**通过门槛**：用户确认需求摘要 + 数据模型草案（逐项确认，不默认、不放大模糊表述）。

**失败处置**：需求不清 → 继续澄清；用户取消 → 停止，不创建任何资源。

**断点标记**：`requirements_confirmed`。

## ① 资源准备

**目的**：配置完备、管理面就绪、RDS Supabase 实例可用、凭据交付、OBS 桶就绪。

**动作**：

⓪ **配置完备性检查**（进入本阶段的第一动作；逐项核对，**缺失项以清单形式显示让用户填写**——不静默失败、不猜测、不跳过）：

| 消费方 | 必需项 | 缺失处置 |
|---|---|---|
| 管理面 MCP | 凭据（devkit 登录 / AK+SK / AUTH_TOKEN 三选一）、`HUAWEICLOUD_PROJECT_ID`、`SUPABASE_RDS_ENDPOINT` | 列出待填 env 名与填写方式；agent 生成含占位符的 mcpServers 骨架，用户从受保护文件填值后重载 |
| frontend/OBS（KooCLI） | AK/SK + `HUAWEICLOUD_REGION`（同时用于 OBS 桶区域） | 同上；region 无法推导时直接向用户询问，不得默认 |

**入口解析规则**：`SUPABASE_RDS_ENDPOINT` 未配置时，凭据就绪后运行 `diagnostics discover`（克隆仓内：`uv run --directory server/mcp_server_rds_supabase_mgr python -m mcp_server_supabase.diagnostics discover`，可加 `--probe`）→ 从 `suggested_env` 勾选项目并采纳推导入口。**推导不了**（项目名非标准区域命名、probe 不可达、discover 报错）→ **明确要求用户指定** `SUPABASE_RDS_ENDPOINT`（提示从控制台获取原生 RDS HTTPS 入口，非 Console 地址）；用户指定前不执行任何实例操作。

a. **管理面就绪**：检测当前已连接 MCP 中是否已有管理面 MCP（devkit 用户登录时预初始化）；无则动态拉起。**安装来源只允许本仓**，两种方式：

- uvx（git 仓模板，推荐）：`--from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr`，入口脚本 `mcp-huaweicloud-rds-supabase-mgr`（env：`SUPABASE_RDS_ENDPOINT`、`HUAWEICLOUD_PROJECT_ID`、凭据模式二选一）
- 本地克隆：`uv run --directory <仓路径>/server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr`

**禁止**从 PyPI 或其他仓库搜索/安装同名或相似包——PyPI 存在第三方 "supabase" MCP 包，非本项目服务器，装上后行为完全错误。拉起后遵循 rds-supabase-mgr-mcp 技能的两阶段确认与执行账本约束。

b. **实例——先问后做**（路由 rds-supabase-mgr-mcp 技能）：**第一步询问用户：新建实例，还是使用已有 RDS Supabase 应用**（不替用户默认）：

- **使用已有应用**：管理面 MCP `list_supabase_applications` 查询全部可用应用 → 以列表展示（application_id / 名称 / 状态 / 规格）让用户选择 → 选定后核验状态（`normal`/running、无进行中任务、网关可达）→ **立即执行 c 凭据获取**（该应用的网关 URL + Anon/Service Role Key——② 数据面 MCP 动态安装的必需输入，**一定不能漏**）
- **新建实例**：`plan_supabase_creation` + `create_supabase_application`（仅 Single 模式；关联已有 PG 或按需新 PG）→ 配置 EIP、安全组（8443 入站规则）、SSL → 创建完成后**同样必须执行 c**。注意：创建安全组不等于应用可访问，须规则放通并核验。

c. **凭据获取（新建与选定已有两条路径都必经——缺失任一项则 ② 数据面 MCP 无法安装，流水线中断）**：所选/所建应用的网关 URL + Anon Key + Service Role Key（**两种 Key 都要**），经管理面 MCP 的 ApiKey 交付工具（deliver 到受保护本地文件）。webapp.json 只记 env 名（`SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`），不记值；instance 段同时记录 `source`（`created` / `selected`）。

d. **OBS 租户桶**（路由 rds-supabase-frontend 技能）：引导用户创建前端托管桶；域名/证书条件此时一并核对，不齐备则在 ⑤ 前补齐。

**通过门槛**：实例 running 且应用实际可访问；凭据已交付（或 devkit 已注入）；桶就绪；instance 段写入 webapp.json。

**失败处置**：配置缺项 → 显示清单让用户填写后重试，不猜测默认值；入口推导不了 → 用户显式指定后再继续；创建任务结果未知 → 管理面账本 `inspect_supabase_plan`，不重复提交；配额/权限不足 → 停止并报告缺项。

**断点标记**：`instance_ready`。

## ② 数据面接入

**目的**：数据面 MCP 就绪并连通 RDS Supabase。

**动作**：按 `rds-supabase-mcp 技能 references/install.md` 动态安装；安装来源同样**只允许本仓**（install.md 的 uvx git 模板，或本地 `uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`），禁止搜索 PyPI 同名包。凭据注入双路径：

- **devkit 优先**：devkit 登录时已注入 → 直接进入验证；
- **半自动兜底**：agent 写 mcpServers 配置骨架（env 为占位符）→ 用户从受保护交付文件复制填值 → 客户端重载。agent 全程不接触密钥明文、不读取交付文件。

**通过门槛**：`get_project_url` 返回与网关地址一致 + `list_tables` 正常应答（连通性以工具调用结果证明，无需 agent 见到明文）。

**失败处置**：401/403 → 核对凭据注入路径；连接失败 → 网关地址/安全组规则；重载后仍失败 → 检查旧环境残留。

**断点标记**：`mcp_connected`。

## ③ 后端生成与部署

**【强制门】** 生成 init.sql 前**必读** rds-supabase-postgres-best-practices 技能（按症状/任务索引规则文件，逐条对照），并参考 rds-supabase-usage 技能的客户端消费视角（表结构/RLS 设计须让 supabase-js 能正确消费）。禁止跳过强制门直接生成。

**动作**：

1. 生成 init.sql：表/索引/RLS 策略/GRANT/种子数据/RPC 函数（Data Function）；可重复执行写法（`IF NOT EXISTS` / `CREATE OR REPLACE` / `ON CONFLICT`）；pgvector 需求 → 向量列 + 索引 + 相似度检索 RPC
2. 部署（路由 rds-supabase-mcp 技能五步）：预检 → 审查（四项：可重复执行/破坏性语句逐条确认/RLS 覆盖/最小授权）→ `execute_sql` 单一事务部署 → 授权暴露（GRANT + `NOTIFY pgrst, 'reload schema'`）→ 查询确认
3. 部署批次记录写入 webapp.json（batch_id/对象清单/init.sql sha256）

**通过门槛**：结构确认（`list_tables`/`list_constraints`）+ RLS 生效（`get_rls_status`/`list_rls_policies`）+ `get_advisors(security)` 无新增 + REST 200（anon key `GET /rest/v1/<表>`）。

**失败处置**：批次失败自动整体回滚（单一事务）→ 修正脚本再部署；advisors 报告 → 按 remediation 处理后复核。

**断点标记**：`backend_deployed`。

## ④ 前端生成

**【强制门】** 生成前**必读** rds-supabase-usage 技能（supabase-js SDK 正确用法：会话管理、RLS 语义、错误契约 `{"error":{code,message,hint}}`），确保生成质量与正确性、避免运行时报错。

**动作**：默认 React + Vite + TypeScript（用户已指定框架则沿用其静态导出方案）；supabase-js 集成（anon key 经 env 注入构建、auth 流、数据查询、Realtime 订阅、pgvector RPC 调用）。凭据中仅 anon key 进入前端产物。

**通过门槛**：`npm run build` 成功 + 本地功能验证（核心流程可走通，"本地应用已验证"语义）。

**失败处置**：构建错误 → 修正；运行时错误 → 对照 usage 技能规则排查 SDK 用法。

**断点标记**：`frontend_built`。

## ⑤ 构建与托管

**目的**：静态产物发布到①预建桶，经 CDN 提供稳定入口。

**动作**（路由 rds-supabase-frontend 技能）：

1. 构建环境核对（Node/包管理器版本，不擅自升级）→ build → 上传①预建租户桶 → CDN 刷新 → 版本记录（`.hwsupabase/frontend/` 契约）
2. **回调回路（⑤↻）**：域名确定后 → 管理面 MCP `update_supabase_auth_config` 配置 site_url / redirect_uris（展示差异后确认）→ 前端按最终地址**重建再发布**。不走此回路会导致 auth 登录回调 404

**通过门槛**：frontend checks 全必需项 passed（entry/assets/routes/negative_paths/cache）+ stable_url HTTPS。

**失败处置**：发布失败 → frontend 技能恢复流程；验收失败 → 按其检查项处置。

**断点标记**：`hosting_published`。

## ⑥ 端到端上线

**目的**：三层组合验证后正式上线并留档。

**动作**：按 references/launch-checklist.md 执行三层验证（后端项/前端项/连通项）→ 输出上线报告（三级交付语义）→ webapp.json 标记 `launched`。

**通过门槛**：全必需项 passed。

**失败处置**：任何必需项 failed → 不标记 launched：后端项失败 → 回③修复重部署；前端项失败 → frontend 修复/回退；连通项失败 → 回调回路/网关/安全组排查。

**断点标记**：`launched`。
