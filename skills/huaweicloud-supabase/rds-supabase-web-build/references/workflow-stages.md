# 步骤 Playbook（步骤一–七）

首次创建流水线的逐步骤执行规范。**三段式**：每步骤 = 输入 → 动作序列 → 输出断言。断言标记：🤖 = `scripts/webapp-gate.py` 机械核验，🔍 = agent 经 MCP 工具或用户确认核验；**两者全过才完成步骤**。断点续作统一规则：会话开始先读 `.hwsupabase/webapp.json`，从 `last_completed_stage` 的下一步骤重入，并**重验该步骤通过条件**——不信任历史结论。加载时机：进入对应步骤执行前（见 SKILL.md 文档加载策略）。

## 执行纪律（全步骤通用）

1. **单次回复推进单一步骤**：一次用户交互最多推进一个步骤；仅当通过条件全过且下一步骤无用户决策点时才可继续
2. **等待协议**：实例创建 job、npm build、CDN 刷新等 >30s 操作 → 固定节奏轮询（job 类每 30 秒一次、上限 20 次）；等待期间**禁止发起任何无关操作**
3. **连续失败中止规则**：同一动作连续失败 2 次 → 强制停止，向用户报告失败原因与下一步选项；**禁止第三次盲目重试**
4. **工具白名单**：各步骤"允许/禁止"为硬边界；确需越界 → 先说明理由获用户同意并记 trace
5. **trace**：每个 MCP/CLI 工具调用后追加一行 `.hwsupabase/trace.jsonl`（格式见 project-state.md，无敏感值）
6. **gate**：动作完成 → 写 webapp.json → 运行 `python <技能目录>/scripts/webapp-gate.py <项目目录> check-stage --stage <标记>`（步骤四、步骤五另跑 `check-gate --number 3|4`）→ **PASS 才输出步骤报告**；FAIL 按缺项整改后重跑

## 步骤一 · 需求澄清

**目的**：将用户的单句需求整理为经确认的需求摘要与数据模型草案。

**输入**：用户单句需求；（已有项目）webapp.json 的 `last_completed_stage`

**动作序列**：

1. 输出步骤声明（格式见 SKILL.md 执行纪律）
2. 澄清清单逐项确认：网站类型与页面清单 / 数据模型草案（实体、关系、对外暴露表）/ 认证需求 / AI 能力识别（pgvector 语义检索、Realtime 订阅、文件上传→v1 默认不含）
3. 边界外识别明确告知（不擅自模拟）：复杂业务逻辑（支付/第三方/长任务）→ v2 FunctionGraph；SSR 不支持
4. 费用预估清单（实例规格/时长、OBS 存储、CDN 流量、域名证书）→ 用户确认
5. 写 webapp.json：`project.requirements_summary`（脱敏）+ history 追加 passed 事件
6. 跑 gate（check-stage --stage requirements_confirmed）→ 步骤报告

**输出断言**：🔍 用户逐项确认需求摘要与数据模型（不默认、不放大模糊表述）｜🤖 gate PASS

**工具白名单**：允许：读写 webapp.json；禁止：**一切 MCP 工具**

**黄金路径**：
```
用户：帮我建一个博客网站，支持登录评论
→ 声明步骤一 → 澄清（页面清单 / Posts-Comments-Users 模型 / 邮箱登录 / 无 AI 能力）
→ 费用清单确认 → 写 webapp.json(requirements_summary)
→ gate PASS → 步骤报告步骤一（下一步骤预告：需要凭据与区域信息）
```

**失败处置**：需求不清 → 继续澄清；用户取消 → 停止，不创建任何资源。**断点**：`requirements_confirmed`

## 步骤二 · 资源准备

**目的**：配置完备、管理面就绪、实例可用（新建或选定已有）、凭据交付、OBS 桶就绪。

**输入**：用户凭据与区域信息（或 devkit 登录态）；上一断点 `requirements_confirmed`

**动作序列**：

1. 声明步骤二
2. **配置完备性检查**（缺项以清单**以清单形式提示用户填写**——不静默失败、不猜测、不跳过）：

   | 消费方 | 必需项 |
   |---|---|
   | 管理面 MCP | 凭据（devkit 登录 / AK+SK / AUTH_TOKEN 三选一）、`HUAWEICLOUD_PROJECT_ID`、`SUPABASE_RDS_ENDPOINT` |
   | frontend/OBS（KooCLI） | AK/SK + `HUAWEICLOUD_REGION`（同时用于 OBS 桶区域） |

3. **入口解析**：`SUPABASE_RDS_ENDPOINT` 未配置 → 凭据就绪后运行 `diagnostics discover`（`uv run --directory server/mcp_server_rds_supabase_mgr python -m mcp_server_supabase.diagnostics discover`，可加 `--probe`）→ 从 `suggested_env` 勾选项目并采纳入口；**无法推导**（非标准区域命名 / probe 不可达 / 报错）→ **要求用户显式指定** `SUPABASE_RDS_ENDPOINT`，指定前不执行任何实例操作
4. **管理面就绪**：检测已连接 MCP（devkit 预初始化）；无则动态启动——**安装来源只允许本仓**：uvx 模板 `git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr`（入口 `mcp-huaweicloud-rds-supabase-mgr`；**生产建议 pin `@<commit>` 锁定版本，避免默认分支变更引入未验证行为**）或本地 `uv run --directory <仓>/server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr`；**禁止**从 PyPI/第三方仓搜索安装（存在同名第三方包）。启动后遵循 mgr-mcp 技能两阶段确认与执行账本
5. **实例——先询问后执行**：**询问用户：新建实例，还是使用已有 RDS Supabase 应用**（不得代用户默认选择）：
   - **已有**：`list_supabase_applications` → 列表展示（application_id/名称/状态/规格）供用户选择 → `show_supabase_application` 核验（normal/running、无进行中任务、网关可达）
   - **新建**：`plan_supabase_creation` + `create_supabase_application`（仅 Single；关联已有 PG 或新 PG）→ 配置 EIP、安全组（8443 入站）、SSL → 等待协议轮询 job；创建安全组 ≠ 可访问，须规则放通并核验
6. **凭据获取（两条路径都必经——缺失任一项则 步骤三 无法安装，流水线中断）**：网关 URL + Anon Key + Service Role Key（**两类密钥均须获取**），经管理面 ApiKey 交付工具 deliver 到受保护本地文件；webapp.json 只记 env 名 + `instance.source`（`created`/`selected`）
7. **OBS 租户桶**（frontend 技能引导，需 AK/SK+region）；域名/证书条件核对，不齐备则 步骤六 前补齐
8. 写 webapp.json instance 段 → gate → 步骤报告

**输出断言**：🔍 配置无缺项（清单回执）｜🔍 实例 running 且实际可访问｜🔍 桶就绪｜🤖 gate PASS（instance 契约 + `source` 枚举）

**工具白名单**：允许：管理面 list/show/plan/create/wait/ApiKey 交付、`diagnostics discover`、frontend 技能 KooCLI（OBS 桶）；禁止：数据面 MCP（尚未安装）、一切 SQL 执行

**黄金路径**：
```
声明步骤二 → 缺项清单（用户填 AK/SK + region + 勾选 discover 候选 cn-north-4/p-123）
→ 问：新建 or 已有？用户：已有
→ list_supabase_applications → 用户选 app-123 → show_supabase_application 核验 normal
→ list_supabase_api_keys + deliver → 受保护文件（agent 不见明文）
→ frontend 技能建桶 obs://webapp-123 → 写 webapp.json(instance.source=selected)
→ gate PASS → 步骤报告步骤二（下一步骤预告：重载客户端后安装数据面 MCP）
```

**失败处置**：配置缺项 → 显示清单提示用户填写后重试；入口无法推导 → 用户显式指定；创建结果未知 → 管理面账本 `inspect_supabase_plan`，不重复提交；配额/权限不足 → 停止报告缺项。**断点**：`instance_ready`

## 步骤三 · 数据面接入

**目的**：数据面 MCP 就绪并连通 RDS Supabase。

**输入**：步骤二 交付的网关 URL + 两把 Key（受保护文件）；上一断点 `instance_ready`

**动作序列**：

1. 声明步骤三
2. 按 `rds-supabase-mcp 技能 references/install.md` 动态安装；**来源只允许本仓**——完整命令：`uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`（或本地克隆 `uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`；服务器文档：https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md ），禁止搜索 PyPI 同名包
3. 凭据注入双路径：**devkit 优先**（已注入 → 直接验证）；**半自动备选路径**（agent 生成含占位符的 mcpServers 配置模板 → 用户从受保护文件复制实际值填入 → 客户端重载；agent 全程不接触明文）
4. 验证：`get_project_url` 返回 == 网关地址；`list_tables` 正常应答
5. 写 webapp.json（stages: mcp_connected）→ gate → 步骤报告

**输出断言**：🔍 `get_project_url` 与网关一致 + `list_tables` 应答（连通性以工具结果证明）｜🤖 gate PASS

**工具白名单**：允许：数据面 `get_project_url`、`list_tables`（仅验证）；禁止：`execute_sql`（步骤四 才用）、一切写工具

**黄金路径**：
```
声明步骤三 → 渲染 install.md 模板（占位符）→ 用户从受保护文件复制实际值填入 → 客户端重载
→ get_project_url == https://gw.example:8443 ✓ → list_tables 应答 ✓
→ 写 webapp.json(mcp_connected) → gate PASS → 步骤报告步骤三
```

**失败处置**：401/403 → 核对凭据注入路径；连接失败 → 网关地址/安全组规则；重载后仍失败 → 检查旧环境残留（连续失败中止规则：连续 2 次失败即停下报告）。**断点**：`mcp_connected`

## 步骤四 · 后端生成与部署

**目的**：强制门对照后生成 init.sql 并单一事务部署。

**输入**：确认过的数据模型；数据面 MCP（步骤三 已连通）；上一断点 `mcp_connected`

**动作序列**：

1. 声明步骤四
2. **【强制门】读 rds-supabase-postgres-best-practices 技能**（按症状/任务索引规则文件）+ rds-supabase-usage 客户端消费视角
3. 生成 init.sql（表/索引/RLS 策略/GRANT/种子/RPC；可重复执行写法 `IF NOT EXISTS`/`CREATE OR REPLACE`/`ON CONFLICT`；pgvector → 向量列+索引+相似度 RPC）
4. **产出规则对照表** `.hwsupabase/gates/3-rules-checklist.md`：best-practices 每条适用规则 → init.sql 对应位置映射（≥5 条映射行，格式 `- <规则> → init.sql L<行号>`）——**gate 校验，缺即拦下**
5. 部署（数据面五步）：预检 → 审查（可重复执行/破坏性语句逐条确认/RLS 覆盖/最小授权）→ `execute_sql` 单一事务 → 授权暴露（GRANT + `NOTIFY pgrst, 'reload schema'`）→ 查询确认
6. 部署批次写入 webapp.json（batch_id/对象清单/init.sql sha256）→ 跑 `check-gate --number 3` + `check-stage --stage backend_deployed` → 步骤报告

**输出断言**：🔍 结构确认（`list_tables`/`list_constraints`）+ RLS 生效（`get_rls_status`）+ `get_advisors(security)` 无新增 + REST 200 且 anon 可见性符合设计（公开表返回数据；受保护表返回空集——RLS 拒绝表现为受限结果，不是 4xx）｜🤖 gate PASS（对照表 ≥5 映射 + deployments 契约 + sha256）

**工具白名单**：允许：数据面全部只读 + `execute_sql`；禁止：管理面写工具（auth 配置属步骤六）、前端构建

**黄金路径**：
```
声明步骤四 → 读 best-practices 索引 → 生成 init.sql（Posts/Users/Comments + RLS + GRANT + RPC）
→ 写 gates/3-rules-checklist.md（8 条规则→SQL 行号）
→ 五步部署：预检 → 审查确认 → execute_sql(单一事务) → NOTIFY pgrst reload schema
→ list_tables 核对 → get_rls_status → get_advisors(security) 无新增 → REST 200 ✓
→ 写 webapp.json(backend.deployments[b1]) → check-gate 3 PASS + check-stage PASS → 步骤报告步骤四
```

**失败处置**：批次失败自动整体回滚（单一事务）→ 修正脚本再部署；advisors 报告 → 按 remediation 处理后复核；连续 2 次部署失败 → 停下报告。**断点**：`backend_deployed`

## 步骤五 · 前端生成

**目的**：强制门对照后生成可构建的前端源码。

**输入**：步骤四 的表结构与 RPC 契约；上一断点 `backend_deployed`

**动作序列**：

1. 声明步骤五
2. **【强制门】读 rds-supabase-usage 技能**（SDK 正确用法：会话管理、RLS 语义、错误契约 `{"error":{code,message,hint}}`）
3. 生成源码（默认 React+Vite+TS + supabase-js；用户已指定框架则沿用其静态导出方案）；anon key 经 env 注入构建；凭据仅 anon key 进产物
4. **产出 SDK 契约对照表** `.hwsupabase/gates/4-sdk-contract-checklist.md`：usage 契约点 → 代码位置映射（会话管理/RLS 语义/错误契约/env 注入/Realtime 清理，≥5 条）——**gate 校验，缺即拦下**
5. `npm run build` → 本地冒烟（首页渲染 + 1 条 RLS 查询 + 1 次 auth 流）——按等待协议处理构建耗时
6. 写 webapp.json（frontend 段）→ 跑 `check-gate --number 4` + `check-stage --stage frontend_built` → 步骤报告

**输出断言**：🔍 构建成功 + 本地冒烟通过（"本地应用已验证"语义）｜🤖 gate PASS（对照表 ≥5 映射 + frontend 契约）

**工具白名单**：允许：数据面只读（对照表结构/RPC 签名）；禁止：`execute_sql`、管理面一切工具

**黄金路径**：
```
声明步骤五 → 读 usage 技能 → 脚手架 react-vite-ts → 实现页面/auth/数据层
→ 写 gates/4-sdk-contract-checklist.md（6 条契约点→代码位置）
→ npm run build ✓ → 本地冒烟（首页渲染 / RLS 查询返回受限数据 / 登录流验证通过）✓
→ 写 webapp.json(frontend.*) → check-gate 4 PASS + check-stage PASS → 步骤报告步骤五
```

**失败处置**：构建错误 → 修正；运行时错误 → 对照 usage 规则排查；连续 2 次同错 → 停下报告。**断点**：`frontend_built`

## 步骤六 · 构建与托管

**目的**：静态产物发布到步骤二预建桶，经 CDN 形成稳定入口，完成回调回路。

**输入**：步骤五 产物源码；步骤二 预建桶与域名/证书；上一断点 `frontend_built`

**动作序列**：

1. 声明步骤六
2. frontend 技能：构建环境核对（Node/包管理器，不擅自升级）→ build → 上传步骤二预建桶 → CDN 刷新 → 版本记录（`.hwsupabase/frontend/` 契约）
3. **回调回路（步骤六↻）**：域名确定 → 管理面 `update_supabase_auth_config` 配 site_url/redirect_uris（展示差异后确认）→ 前端按最终地址**重建再发布**。未执行此回路 = auth 登录回调 404
4. frontend checks（entry/assets/routes/negative_paths/cache）
5. 写 webapp.json（hosting_published）→ gate → 步骤报告

**输出断言**：🔍 frontend checks 全必需项 passed + stable_url HTTPS｜🤖 gate PASS

**工具白名单**：允许：管理面 `update_supabase_auth_config`、frontend 技能工具链（KooCLI/OBS/CDN/npm）；禁止：`execute_sql`、实例级管理面写（删除/改密等）

**黄金路径**：
```
声明步骤六 → 构建环境核对 → npm run build → 上传 obs://webapp-123/v1 → CDN 刷新
→ 用户确定域名 https://demo.example.com → update_supabase_auth_config(site_url + redirect_uris，差异确认)
→ 前端重建再发布 v2 → frontend checks 全 passed（entry 2xx / assets 2xx / routes / 404 路径 / cache 头）
→ 写 webapp.json(hosting_published) → gate PASS → 步骤报告步骤六
```

**失败处置**：发布失败 → frontend 技能恢复流程；验收失败 → 按其检查项处置；回调配置失败 → 重试差异确认（连续失败中止规则）。**断点**：`hosting_published`

## 步骤七 · 端到端上线

**目的**：三层组合验证后正式上线并留档。

**输入**：步骤六 的 stable_url 与版本记录；上一断点 `hosting_published`

**动作序列**：

1. 声明步骤七
2. 按 references/launch-checklist.md 执行三层验证：后端项（结构/RLS/advisors/REST 200 + anon 可见性）/ 前端项（checks 契约）/ 连通项（站点渲染、前端→API 数据可见性、**多用户隔离抽检**——两个测试账号经数据面 MCP 用户管理创建后互访对方数据行断言不可见、auth 回调跳转）
3. 输出上线报告（三级交付语义 + stable_url + 版本引用）
4. 写 webapp.json（launched）→ gate → 完成交付

**输出断言**：🔍 三层全必需项 passed（含多用户隔离抽检不可见）｜🤖 gate PASS（launched 终态 + 全链 history）

**工具白名单**：允许：数据面只读与用户管理（测试账号创建）、frontend checks；禁止：**一切写工具**（上线验证除测试账号外纯只读；测试账号在报告后提示用户可清理）

**黄金路径**：
```
声明步骤七 → 后端项（get_rls_status / get_advisors / REST 200 + anon 可见性）→ 前端项（checks 契约复核）
→ 连通项（stable_url 渲染 ✓ / 站点内查询可见性正确 ✓ / 隔离抽检：账号 A↔B 互访均空集 ✓ / auth 回调 ✓）
→ 上线报告（本地已验证 / 环境已准备 / 线上验收通过）→ 写 webapp.json(launched)
→ gate PASS → 交付
```

**失败处置**：后端项失败 → 回步骤四修复重部署；前端项失败 → frontend 修复/回退；连通项失败 → 回调回路/网关/安全组排查——不标记 launched。**断点**：`launched`
