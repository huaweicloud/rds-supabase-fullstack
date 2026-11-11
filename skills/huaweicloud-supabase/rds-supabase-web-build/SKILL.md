---
name: rds-supabase-web-build
description: 'RDS Supabase 全栈开发编排技能：AI Agent 通过自然语言创建并托管 Web 应用网站的端到端工作流——需求澄清与设计、前端代码生成、后端声明式配置（DDL/GRANT/RLS/RPC）生成与部署、本地 L0 测试验证、前端静态资源 OBS+CDN 全托管、端到端上线与生命周期管理（更新/回滚/下线）。Use when：创建 Web 网站、搭建 AI 应用、全栈应用从零到上线、已有 RDS Supabase 应用的迭代更新与托管维护。编排管理面与数据面两台 MCP（均由工作流步骤动态安装：管理面→步骤三、数据面→步骤四）及 rds-supabase-mgr-mcp / rds-supabase-mcp / rds-supabase-usage / rds-supabase-frontend / rds-supabase-postgres-best-practices / rds-supabase-function-graph 六个专项技能。v1 后端边界为数据层；复杂业务逻辑由 function-graph 技能（云函数）承接，SSR 后端部署不支持。'
license: MIT
metadata:
  version: "0.11.5"
---

# RDS Supabase 全栈开发编排（web-build）

## 概述

RDS Supabase 全栈开发的**顶层编排技能**：用户以单句自然语言需求（如"创建一个网站"）触发，AI Agent 完成前端与后端的代码生成、部署运行、托管上线的完整链路。本技能是厚工作流编排者——内置步骤状态机、通过条件、失败处置与断点续作；各环节深度内容由专项技能承载，本技能仅执行路由，不复制内容。

双工作流总图：

```
【首次创建流水线】（每步骤设有通过条件；未满足不得推进）
 步骤一 环境检查与配置 → 步骤二 需求澄清与设计 → 步骤三 资源准备 → 步骤四 数据面接入
                ↳ 环境四项：凭据 · Region · RDS/OBS 接入点 · PROJECT_ID（缺失显式提醒用户设置）
 步骤五 后端生成部署 → 步骤六 前端生成 → 步骤七 本地测试验证 → 步骤八 构建与托管 → 步骤九 端到端上线
                ↳ 步骤三动态启动管理面 MCP（实例/EIP/安全组/SSL/密钥）+ OBS 租户桶
                ↳ 步骤四动态安装数据面 MCP（install.md）
 步骤八↻ 回调回路：域名确定 → 管理面配置 site_url/redirect_uris → 前端重建

【生命周期循环】（独立工作流）
 更新（增量 init.sql → 重走步骤五与步骤九）｜回滚（前端版本回退 + DB 批次管理）｜下线（清理清单）｜密钥轮换
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
| 复杂业务逻辑（支付/第三方调用/长任务） | rds-supabase-function-graph 技能（云函数承载） |

## 前置条件

1. 技能包（全部技能）已按 [README](README.md)/[INSTALL.md](INSTALL.md) 完整安装进**项目级**技能目录（**强约束：仅项目级，路径固定**——CodeArts `<项目根>/.codeartsdoer/skills/`、opencode `<项目根>/.opencode/skills/`、Claude Code `<项目根>/.claude/skills/`；**禁系统内置/系统级目录与一切个人级目录**（`~/.codeartsdoer/skills` 等同名不同根的家目录路径）——技能版本随项目走，不污染其他项目）——安装阶段不含 MCP 与凭据
2. uv（含 uvx）可用——步骤三/四动态安装 MCP 所需，步骤一环境检查核对，缺失提醒用户安装
3. 步骤一执行环境检查与配置：凭据、Region（局点）、RDS 与 OBS 接入点、`HUAWEICLOUD_PROJECT_ID` 须已在**项目内配置**（webapp.json `environment` 段 + `secrets/`，唯一权威）或可解析（discover 解析结果**写回项目配置**）；**无法获取的项必须以缺失清单显式提醒用户设置**，不得猜测或跳过，**不从 agent 进程/全局环境变量读取**（红线见注意事项）
4. 云侧付费资源（实例/OBS 桶/CDN）创建前须用户显式确认（费用预估在步骤二输出）

## 工作流（步骤一–八 分步执行）

**步骤状态机**（断点续作依据，记录于 `.hwsupabase/webapp.json` 的 `last_completed_stage`）：

```
environment_ready → requirements_confirmed → instance_ready → mcp_connected
                  → backend_deployed → frontend_built → local_verified → hosting_published → launched
```

每步固定节奏：**步骤声明 → 编号动作 → 写 webapp.json → gate PASS → 步骤报告**。各步的完整 playbook（输入/输出断言/工具白名单/黄金路径/失败处置）见 references/workflow-stages.md 对应小节。

### 步骤一 · 环境检查与配置 → 断点 `environment_ready`

**配置来源唯一权威：当前项目的 `.hwsupabase/`**（webapp.json `environment` 段 + `secrets/`）——Region/接入点/PROJECT_ID **不从 agent 进程环境、shell 会话或全局环境变量读取**（同名变量可能来自其他项目或本机全局设置，一律不采信）；`HUAWEICLOUD_REGION` 等环境变量名仅在步骤三/四启动 MCP 时**由项目配置注入进程**（进程作用域，不 export）

1. **凭据检查（四选项交互确认，禁止跳过）**：以选择清单呈现凭据来源，未获用户勾选不得推进——**A** 项目内 `secrets/`（AK/SK 或 Token，0600、排除 Git，勾选即采用）；**B** 项目内 devkit 凭据文件（`HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE` 指向项目内 0600 文件，勾选即采用）；**C** 感知到的系统/用户级凭证配置（全局 devkit 登录态、`~/.config/huaweicloud/`、`~/.obsutilconfig`、环境变量中的 AK/SK 等）——**不得直接采用**，逐项**显示**（级别 / 来源文件或变量名 / 账号标识，**不显示明文**）经用户确认后采用并记 `credential_source=external_confirmed`，未确认即不采用；**D** 用户指定或输入（给出凭据文件路径，或交互输入 AK/SK/Token → 落盘项目 `secrets/`，0600、排除 Git，agent 不回显、不记录明文）；均无 → 提醒用户经 D 提供
2. **uv（含 uvx）可用**——步骤三/四动态安装 MCP 的前提；缺失 → 提醒用户安装（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
3. **Region（局点）确认**：读项目配置（webapp.json `environment.region`）；缺失 → 显式提醒用户告知局点并**写入项目配置**（不读进程/全局环境变量）
4. **RDS 接入点**：项目配置已有 → 采用；缺失且凭据就绪 → `diagnostics discover` 解析并经用户勾选，**结果写回项目配置**；无法解析 → 显式提醒用户设置
5. **OBS 接入点**：按 Region 推导（`obs.<region>.myhuaweicloud.com`）→ **连接测试**（`dig +short` 有解析 + `curl -sI --max-time 10` 有 HTTP 响应——任意状态码即通，4xx 属未认证预期）→ 通过则**写回项目配置**；**无法推导或测试不通 → 提示用户输入**实际接入点（输入后复测，通过才写回）
6. **PROJECT_ID**：项目配置已有 → 采用；缺失 → discover 勾选并**写回项目配置**；无法获取 → 显式提醒用户设置
7. **五项终检（写入 environment_ready 前的最后一道校验，全部通过才算就绪）**：**REGION、AK/SK、PROJECT_ID、RDS_ENDPOINT、OBS_ENDPOINT 逐项核验正确无误**——前四项以一次 `diagnostics discover` 实际调用同时验证（凭据有应答=AK/SK 正确；局点可解析=REGION 有效；应答含该值=PROJECT_ID 正确；endpoint 可达=RDS_ENDPOINT 正常，可加 `--probe`；AK/SK 凭据须带 `SUPABASE_TRANSPORT=sdk_core`），OBS_ENDPOINT 按第 5 项连接测试规则复测；任一项不通过 → 对接卡片反馈用户（哪项、实测现象）→ **二次输入确认**（用户修正后仅复测该项）→ 通过才计入就绪；仍不通过 → 如实报告，**不写 `environment_ready`**（禁止带病通过）
8. 缺失项汇总为清单提醒用户逐项设置，**不得猜测、不得跳过、不得以默认值代替**；全部就绪且终检通过 → 写 webapp.json（`environment` 段 + `environment_ready`）→ gate PASS

### 步骤二 · 需求澄清与设计 → 断点 `requirements_confirmed`

1. **多轮澄清或 SDD 规格驱动**：围绕「场景 × 功能 × 边界」多轮收敛——目标用户与使用情境、页面清单、数据模型、认证需求、**文件/图片/视频管理诉求**、AI 能力（pgvector 检索/Realtime）；纪律：**不遗留**（清单逐项确认）、**不发散**（偏离场景的诉求记录为备注不入主线）、**聚焦不走偏**（每轮复述共识与用户校准）
2. **网站设计指标——交互式逐项确认**：以设计指标卡呈现五维综合设计要求，经用户确认后记入 `project.design_requirements`——**网站风格**（简约现代/商务专业/活泼年轻/暗色科技/自定义描述，结合目标用户推荐）；**界面设计**（导航结构、响应式优先级默认移动优先、组件库偏好）；**美观度**（`prototype` 原型级 / `standard` 标准级（默认）/ `premium` 精品级——动效与细节打磨）；**复杂度**（`simple` ≤3 页 / `medium` 4–8 页（默认）/ `rich` >8 页富交互——与页面清单联动核对）；**功能性交互反馈**（loading/错误提示/空状态，默认全套基础反馈——与功能矩阵联动）
3. **BaaS 能力提炼与满足性评估**：映射 RDS Supabase 能力清单（数据建模/CRUD、Data-Function RPC、认证、**Storage 文件存储**、Realtime、pgvector）逐项评估，记入 `project.baas_capabilities`；**存在文件/图片/视频管理诉求 → 标记 `storage` → 步骤三必须完成专用私有 OBS 桶准备与 `update_supabase_storage` 对接（禁止复用前端托管桶——公开读桶复用即权限越界与隐私暴露）**
4. 边界外识别（复杂业务逻辑→FunctionGraph；SSR 不支持）+ 费用预估清单（实例、前端托管桶、Storage 桶分别列示）→ 用户确认
5. 写 webapp.json（requirements_summary + baas_capabilities + design_requirements）→ gate PASS

### 步骤三 · 资源准备 → 断点 `instance_ready`

1. 复核步骤一环境配置（凭据 / Region / RDS·OBS 接入点 / PROJECT_ID）仍就绪；发现缺项 → 返回步骤一补齐
2. **动态启动管理面 MCP**（已连接则跳过）。**安装时机硬门槛**：凭据（AK/SK 或 Token）、Endpoint、Region、PROJECT_ID 四项**全部正确获取并核验后才开始安装**——任一项缺失即返回步骤一补齐，不带着配置缺口反复尝试安装（否则将持续报凭据/接入点类故障）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板（推荐）
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
   ```

   **网络逃生通道**：uvx git 拉取失败或停滞（含代理后仍不通；连续失败 2 次或 30 秒无进展即判失败）→ **立即切换** ZIP 归档 + 本地运行，不反复重试：

   ```bash
   TMP=$(mktemp -d)   # 下载物一律落唯一临时目录，不污染项目目录与家目录
   curl -L --fail --max-time 120 -o "$TMP/rds-supabase-fullstack.zip" \
     https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
   unzip -q "$TMP/rds-supabase-fullstack.zip" -d "$TMP"
   uv run --directory "$TMP/rds-supabase-fullstack-main/server/mcp_server_rds_supabase_mgr" mcp-huaweicloud-rds-supabase-mgr
   # 临时目录在 MCP 运行期间必须保留（uv run 指向它）；MCP 停止后 rm -rf "$TMP" 清理
   ```

   ZIP 归档属本仓官方源（`.../archive/<commit>.zip` 为 pin 等价形式），不违反来源锁定；仍禁 PyPI/第三方源。
   env：`SUPABASE_RDS_ENDPOINT` / `HUAWEICLOUD_PROJECT_ID` / 凭据——**值一律由项目内配置注入进程**（步骤一 `environment` 段与 `secrets/`），不读取会话/全局环境。**凭据模式二选一**：REST token（`HUAWEICLOUD_AUTH_TOKEN`，`SUPABASE_TRANSPORT` 默认 rest）或 **AK/SK（必须设置 `SUPABASE_TRANSPORT=sdk_core`**，读取 `HUAWEICLOUD_ACCESS_KEY`/`HUAWEICLOUD_SECRET_KEY`/可选 `HUAWEICLOUD_SECURITY_TOKEN`）——用户已填 AK/SK 而未设 `sdk_core` 时管理面将按 REST 模式启动并因缺 Token 失败；devkit 优先；或 `diagnostics discover` 勾选；或半自动方案：配置模板含占位符，由用户填入实际值

   **网络与验证纪律**：**默认不走代理直连局点**（内网/专线环境经代理转发易引入链路故障；**禁止上来就走代理**——代理是兜底项而非默认项）；安装完成后执行**连接验证**：MCP 连接 OK 且任一**查询类工具**（优先 `get_supabase_capabilities`，一个即可）正常返回，验证通过才算安装成功；直连验证失败 → 先核对网络可达性、凭据模式（AK/SK 须 `sdk_core`）与 Endpoint，**确认直连不可达后**再显式配置代理并复验

   **注册纪律（项目级隔离）**：MCP 启动后**只注册进当前项目的项目级 MCP 配置**（Claude Code `<项目根>/.mcp.json`、CodeArts `<项目根>/.codeartsdoer/`、OfficeAce 项目根下项目级配置、opencode `<项目根>/opencode.json`；**禁止 `~/.claude.json` user scope、Claude Desktop `claude_desktop_config.json`、`~/.config/opencode/` 等一切用户级/系统级位置**——用户级注册会使本机其他项目可见可用，属边界溢出；宿主仅有用户级机制 → 停止报告，不注册）；含凭据的配置文件列入 `.gitignore`（0600）；**严禁 `uv tool install`/`pip install` 装入用户级/系统级**——uvx 仅一次性缓存运行；注册后核验落位再重载客户端（详细表见 workflow-stages.md 步骤三）
3. **Supabase 应用接入方式——交互式勾选（禁止跳过）**：以选择清单呈现「使用已有应用 / 新建应用」二选一，未获用户显式选择不得推进，不得代为默认。**使用已有** → `list_supabase_applications` 候选列表（ID/名称/状态/规格）供用户勾选 + `show_supabase_application` 状态核验；**新建** → 创建（仅 Single）+ 配置 EIP/安全组 8443/SSL
4. **凭据获取（两条路径均必须执行，不得遗漏）**：网关 URL + Anon/Service Role Key → 受保护文件（步骤四安装所必需）
5. **OBS 桶接入方式——交互式勾选（禁止跳过）**：以选择清单呈现「使用已有桶 / 新建桶」二选一，未获用户显式选择不得推进，不得代为默认（frontend 技能引导）。**使用已有** → 列出租户桶并**仅保留满足静态托管条件的公开读桶**（非公开桶一律剔除、不入候选）供用户勾选 + 区域与托管能力核验；**新建** → **桶名默认与应用名称保持一致**（英文化：小写字母/数字/连字符，3–63 字符；**名称冲突追加短 uuid 后缀**），经用户确认后由 frontend 技能创建——**创建前展示桶配置卡**（存储类别**多 AZ 优先**；**阻止公网访问必须关闭**——该开关开启则匿名读被拒、静态托管不可用；**桶策略固定公共读**：仅匿名 GetObject，不可改为其他），创建后**回读核验三项实际生效**
6. **Storage 存储对接（仅当步骤二标记 `storage` 能力；**步骤三不无条件创建后端 OBS 桶**——桶的创建仅发生在「存储诉求存在 且 所选实例尚未对接」时）**：**对接状态先行判定（承接第 3 项应用接入方式的勾选结果，不另行选择、不改变该二选一流程）**——勾选「使用已有应用」→ 经管理面确认其 Storage 对接状态：**已对接 OBS → 复用既有对接，不新建桶、不重复对接**（`storage.source=existing`）；未对接（含「新建实例」）→ 进入桶准备流程，交互式勾选「使用已有桶 / 新建桶」（纪律同上，禁止跳过）。**使用已有桶** → **桶策略安全评估**：必须私有（无公开读、无匿名 GetObject、无公开列举），存在任一公开项即判定不合理 → 停止并建议转新建或先修正策略；**新建桶** → **动态创建私有桶**（访问类型固定私有，禁止公开读）+ 最小权限，桶名建议 `<应用slug>-storage`。**两类均禁止复用前端托管桶**（公开读桶复用即权限越界）→ 经管理面 `update_supabase_storage` 对接（凭据经 request_ref、两阶段确认；首次启用需 SK）→ 写 webapp.json instance/obs/mcp/storage 段 → gate PASS

### 步骤四 · 数据面接入 → 断点 `mcp_connected`

1. **动态安装数据面 MCP**（实例凭据就绪后）。安装方式唯一二选一，**不得另寻来源**：

   ```bash
   # git 模板
   uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   # 本地克隆
   uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
   ```

   **网络逃生通道**：uvx git 拉取失败或停滞（含代理后仍不通；连续失败 2 次或 30 秒无进展即判失败）→ **立即切换** ZIP 归档 + 本地运行，不反复重试：

   ```bash
   TMP=$(mktemp -d)   # 下载物一律落唯一临时目录，不污染项目目录与家目录
   curl -L --fail --max-time 120 -o "$TMP/rds-supabase-fullstack.zip" \
     https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
   unzip -q "$TMP/rds-supabase-fullstack.zip" -d "$TMP"
   uv run --directory "$TMP/rds-supabase-fullstack-main/server/mcp_server_rds_supabase" mcp-server-huaweicloud-rds-supabase
   # 临时目录在 MCP 运行期间必须保留（uv run 指向它）；MCP 停止后 rm -rf "$TMP" 清理
   ```

   ZIP 归档属本仓官方源（`.../archive/<commit>.zip` 为 pin 等价形式），不违反来源锁定；仍禁 PyPI/第三方源。
   env：`SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`（agent 生成含占位符的配置模板 → 用户从受保护文件复制实际值填入 → 客户端重载）

   **访问协议跟随实例 SSL 状态**：实例开启 SSL → `https://`；未开启 SSL → `http://`（**不强制 HTTPS 交互**）。步骤三将 `instance.ssl_enabled`（true/false）记入 webapp.json；gate `--verify` 据此放行 http——`ssl_enabled=false` 时 HTTP 即预期访问方式

   注册纪律与步骤三相同：数据面 MCP **只注册进当前项目的项目级配置**（同表同禁令；宿主仅有用户级机制 → 停止报告，不注册），严禁用户级/系统级；**网络纪律同步骤三**：默认直连不走代理（禁止上来就走代理），装后以查询工具验证连接
2. 验证：`get_project_url` == 网关地址 + `list_tables` 应答 → 写 webapp.json → gate PASS

### 步骤五 · 后端生成部署 → 断点 `backend_deployed`

1. **【强制门】** 读 best-practices（逐条对照）+ usage 客户端消费视角
2. 生成 init.sql + **一键清理脚本 `teardown.sql`**（与 init.sql 同源生成，供下线/换实例时一键执行：单事务包裹、全语句 `IF EXISTS` 幂等、依赖安全序 策略→触发器→表→函数/RPC→角色→schema、仅覆盖部署清单内对象；gate 校验对象全覆盖）+ **规则对照表** `gates/3-rules-checklist.md`（gate 校验）
3. 五步部署：预检 → 审查 → `execute_sql` 单一事务 → 授权（`NOTIFY pgrst, 'reload schema'`）→ 查询确认
4. 验证：结构确认 + RLS 生效 + advisors 无新增 + REST 200 且 anon 可见性符合设计 → 写 webapp.json（含 `exposed` 对外表清单与 `backend.teardown_ref`）→ gate `--verify` PASS（机器验真）

### 步骤六 · 前端生成 → 断点 `frontend_built`

1. **【强制门】** 读 usage（SDK 正确用法，避免运行时报错）
2. 生成源码（默认 React+Vite+TS + supabase-js；**按 `project.design_requirements` 执行**——风格/美观度分级决定视觉与细节投入，复杂度分级约束页面与交互规模；仅 anon key 进产物）+ **SDK 契约对照表** `gates/4-sdk-contract-checklist.md`（gate 校验）
3. `npm run build` + 本地冒烟（首页渲染 / 1 条 RLS 查询 / 1 次 auth 流）→ 写 webapp.json → gate PASS

### 步骤七 · 本地测试验证 → 断点 `local_verified`

1. **本地联调**：本地运行前端（dev server 或构建产物预览），supabase-js 直连已部署后端网关（步骤五真实数据面）——前端本地部署、与后端对接
2. **L0 用例孵化**：从步骤二确认的功能场景逐项孵化 **L0 级用例**（每场景 ≥1 条正向 + 关键负向；覆盖页面渲染、核心 CRUD 交互、认证流、RLS 数据可见性、错误路径），用例清单（T 编号）经用户确认——只覆盖已确认场景，不发散
3. **执行与修复 Loop**：逐条执行并记录结果 → 失败项定位修复（前端缺陷改前端；后端问题回步骤五增量批次重部署）→ **循环直至全部用例通过**（同用例连续 2 次失败 → 中止报告）；产出 `.hwsupabase/gates/5-local-test-report.md`（gate 校验：≥5 条 passed、零 failed）
4. 写 webapp.json（local_verified）→ gate（check-stage + check-gate --number 5）PASS

### 步骤八 · 构建与托管 → 断点 `hosting_published`

1. frontend 技能：build → 上传步骤三预建桶 → 版本记录（CDN 刷新仅正式模式）。**托管入口协议跟随实例 SSL**：`ssl_enabled=true` → HTTPS 入口（域名/证书就绪）；`false` → HTTP 入口（无需证书，**不得 HTTPS**——HTTPS 页面调用 HTTP 网关属混合内容，被浏览器拦截，站点不可用）
2. **托管场景选择——交互式勾选（禁止跳过）**：产物上传后、入口配置前，向用户呈现两种场景方式并确认，未获用户确认不得推进：
   - **临时访问（原型验证/测试验证）**：**无需购买正式域名与 ICP 备案**，确定性自动配置——① 域名固定 `<应用名英文化>.huaweicloud-rds.com`（slug 规则同桶名；为空/冲突追加短 uuid）；② OBS 域名管理为托管桶**新增该自定义域名**；③ 解析 OBS endpoint IP → **hosts 追加** `IP → 域名` 映射（按 OS 定位与命令，**只追加带标记行、禁止破坏已有映射**，先备份、经用户确认执行）；④ `curl`/浏览器验证可达。明示局限（本机映射、非正式商用入口）与升级路径（可转正式模式）
   - **正式上线（线上商用）**：购买域名 → 实名认证 → ICP 备案（中国大陆区域）→ 绑定自有域名 → 接入 CDN 加速与 HTTPS 证书（obs-cdn 路线）——完整商用链路
   选择记入 webapp.json `frontend.hosting_mode`（`temporary`/`production`，gate 校验）
3. **步骤八↻ 回调回路**：域名确定（按所选场景入口，协议跟随实例 SSL）→ `update_supabase_auth_config` 配 site_url/redirect_uris（差异确认）→ 前端按最终地址**重建再发布**
4. 验证：frontend checks 全必需项 passed + **stable_url 协议跟随实例 SSL**（gate 读 frontend record 机器核验与 `ssl_enabled` 一致）→ 写 webapp.json（含 `hosting_mode`）→ gate PASS

### 步骤九 · 端到端上线 → 断点 `launched`

1. 三层验证（launch-checklist）：后端项 / 前端项 / 连通项（站点渲染、API 可见性、**多用户隔离抽检**、auth 回调）；抽检测试账号创建后即记入 webapp.json `test_accounts`（email/密码/用途）
2. 上线报告（三级交付语义）→ 写 webapp.json → gate `--verify` PASS
3. **输出「应用名片」并落盘 `.hwsupabase/app-card.md`**（launched 后最终交付物）：应用名称、功能介绍、访问地址、后端地址、**测试账号（含密码）**、数据模型与技术栈概览、使用方式（更新/回滚/下线触发语）——格式见输出格式

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
6. **gate 机械核验**：步骤完成前运行本技能 `scripts/webapp-gate.py`（`check-stage --stage <标记>`；步骤五、六、七另跑 `check-gate --number 3|4|5`），**PASS 才能输出步骤报告与推进**；FAIL 按缺项整改后重跑。**步骤五与步骤九的 `check-stage` 必须加 `--verify`（步骤五另加 `--mcp-command <数据面启动命令>`）**：云上事实（REST 可达/对外表 anon 可见性/RLS/advisors）由 gate 直连机器核验，不采信 agent 自报
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
| 步骤三 资源接入方式（Supabase 应用 / OBS 桶） | 交互式勾选，禁止跳过；未获显式选择不得推进、不得代为默认；已有桶候选仅含公开读桶；新建桶名默认与应用名英文化一致，名称冲突追加短 uuid 后缀 |
| init.sql（步骤五产出） | best-practices 四项审查通过；破坏性语句逐条人工确认 |
| 凭据 | agent 永不接触明文；只处理 env 名与注入状态；连通性以工具调用结果证明 |
| 回调配置（步骤八↻） | 展示 site_url/redirect_uris 差异后确认 |

## 输出格式

- **进度看板**（全程维护，双轨呈现）：
  - **宿主待办联动**：触发后第一动作创建八项待办（对应步骤一~八）；进入步骤置"进行中"、gate PASS 置"已完成"、失败置"受阻"
  - **聊天内步骤总览**（强制展示，不依赖宿主待办工具是否可见）：首条回复即输出下方全表；此后**每次步骤报告头部完整重发**（状态刷新）；状态标记：⏳ 待办 / 🔄 进行中 / ✅ 已完成 / ⛔ 受阻；重入会话时依据 webapp.json 重建双轨看板

  ```
  【项目步骤总览】
  | # | 步骤 | 通过断点 | 状态 |
  |---|---|---|---|
  | 一 | 环境检查与配置 | environment_ready | 🔄 进行中 |
  | 二 | 需求澄清与设计 | requirements_confirmed | ⏳ 待办 |
  | 三 | 资源准备 | instance_ready | ⏳ 待办 |
  | 四 | 数据面接入 | mcp_connected | ⏳ 待办 |
  | 五 | 后端生成部署 | backend_deployed | ⏳ 待办 |
  | 六 | 前端生成 | frontend_built | ⏳ 待办 |
  | 七 | 本地测试验证 | local_verified | ⏳ 待办 |
  | 八 | 构建与托管 | hosting_published | ⏳ 待办 |
  | 九 | 端到端上线 | launched | ⏳ 待办 |
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
- **上线报告**（步骤九）：三级交付语义（本地已验证/环境已准备/线上验收通过）+ stable_url + 前端版本记录引用；格式见 references/launch-checklist.md
- **应用名片**（步骤九 launched 后输出 + 落盘 `.hwsupabase/app-card.md`）：

  ```
  【应用名片】<应用名称>
  | 项 | 内容 |
  |---|---|
  | 应用名称 | <project.name> |
  | 功能介绍 | <requirements_summary 一句话> |
  | 访问地址 | <stable_url>（temporary 场景仅本机生效） |
  | 后端地址 | <gateway_url>（RDS Supabase 网关） |
  | 测试账号 | A：<email> / 密码：<password>；B：<email> / 密码：<password>（验收演示账号，正式使用前改密或删除） |
  | 数据模型 | <N> 张表：<表清单>；RPC <M> 个 |
  | 技术栈 | 前端 <framework> + supabase-js；后端 Supabase（PostgREST/GoTrue）；托管 OBS · <hosting_mode> |
  | 版本信息 | 后端批次 <current_batch> · 上线 <时间> |
  | 项目管理 | 状态 .hwsupabase/webapp.json · 前端记录 <record_ref> |

  使用方式（自然语言直接说）：
  - 更新：「给 <应用名> 增加 <功能/页面>」
  - 回滚：「回滚 <应用名> 前端到上个版本」
  - 下线：「下线 <应用名>」（含清理清单）
  ```
- **失败/断点报告**：当前步骤、失败原因（含连续失败中止规则触发）、已恢复/待人工项、webapp.json 状态

## 验证方法

- 每步骤通过条件即验证点（见工作流表与 workflow-stages.md）
- 步骤九 上线通过条件 = 三层组合（后端项/前端项/连通项），完整清单见 references/launch-checklist.md
- 上线后复查：webapp.json 标记 launched 且 stable_url 可访问

## 注意事项

- **凭据红线**：密钥永不写入 webapp.json/会话内容/工具返回；agent 不读取交付文件；凭据三层优先级（项目 `secrets/` → 项目内 devkit 文件 → 全局 devkit 显式确认）；anon key 进入前端产物属预期，Service Role Key 绝不进入；**唯一例外**——步骤九 验收创建的**应用级测试账号**（邮箱+密码）记入 `test_accounts` 并随「应用名片」交付用户：属应用演示账号而非云凭据（正式使用前改密或删除）
- **环境配置项目级隔离（红线）**：Region / RDS·OBS 接入点 / PROJECT_ID 的**唯一权威是项目内 webapp.json `environment` 段**——**禁止从 agent 进程环境、shell 会话或全局环境变量读取同名变量**（可能来自其他项目或本机全局，跨项目共享即边界溢出）；`diagnostics discover` 解析结果必须写回项目配置；`HUAWEICLOUD_REGION` 等环境变量名仅在步骤三/四启动 MCP 时由项目配置注入进程（进程作用域，不 export）；凭据四选项交互（禁止跳过）：A 项目 `secrets/` 与 B 项目内 devkit 文件（`HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE` 指向项目内 0600 文件）勾选即采用；**C 感知到的系统/用户级凭证配置（全局 devkit、`~/.config/huaweicloud/`、`~/.obsutilconfig`、环境变量）不得直接采用**——逐项显示（级别/来源/账号标识，不显明文）经用户确认后采用并记 `credential_source=external_confirmed`；D 用户指定或输入落盘项目 `secrets/`——多项目共用一台机器时，A 项目的凭证配置不得静默进入 B 项目
- **凭据项目级隔离（红线）**：登录态与凭据**只存放于当前项目内**——`<项目根>/.hwsupabase/secrets/`（0600、属主本人、目录排除 Git）。**禁止**写入全局或系统环境变量（shell profile、launchd/系统级 env、会话 `export`）；**禁止**新建或覆写个人级配置（`~/.config/huaweicloud/credentials.json`、`~/.obsutilconfig`）——已有个人级文件属既有工具与其他项目，**不迁移、不删除、不覆写**。MCP 进程凭据经进程内 env 或项目内凭据文件注入（`HUAWEICLOUD_MCP_CREDENTIALS_FILE` / `HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE` 指向项目内 0600 文件；`SUPABASE_REQUESTS_FILE=<项目>/.hwsupabase/requests.json`，Key 交付落盘 secrets/）。本项目凭据轮换只影响本项目 `.hwsupabase/`，不污染其他项目开发
- **MCP 注册项目级隔离（红线）**：动态安装的两台 MCP **只注册进当前项目的项目级 MCP 配置**——Claude Code `<项目根>/.mcp.json`（`mcpServers` 结构）、CodeArts `<项目根>/.codeartsdoer/`（与项目级技能目录同根）、OfficeAce 项目根下该宿主项目级配置、opencode `<项目根>/opencode.json` 或 `.opencode/` 内配置（`mcp` 键）；**禁止一切用户级与系统级位置**（`~/.claude.json` user scope、Claude Desktop `claude_desktop_config.json`、`~/.config/opencode/` 全局、`~/.codeartsdoer/` 个人级、系统 managed 配置等）——用户级注册会使本机其他项目可见并使用本项目实例的 MCP 与凭据，属边界溢出；**宿主仅有用户级配置机制 → 停止并报告，不注册**（宁缺毋溢出）；注册后核验条目落位项目级且未触碰用户级/系统级，再重载客户端；含凭据的配置文件必须列入 `.gitignore`（0600，凭据由用户从 secrets/ 填入，agent 不经手明文）；**严禁 `uv tool install`/`pip install` 等装入用户级/系统级环境**——`uvx` 仅一次性缓存运行（共享构建缓存非安装非注册），本地克隆 `.venv` 只落仓内目录（项目级或唯一临时目录）；下线时从项目级配置移除两台条目
- **MCP 安装来源锁定**：两台 MCP 服务器只从**本仓**安装（uvx git 模板 `git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=...`，本地 `uv run --directory server/... <入口脚本>`，或**网络逃生通道**：git 不可达时立即切换 ZIP 归档下载解压 + 本地运行——`https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip`，连续失败 2 次或 30 秒无进展即切换，不反复重试；`.../archive/<commit>.zip` 为 pin 等价形式）；禁止从 PyPI/第三方仓库搜索安装——存在同名第三方 "supabase" MCP 包，会导致连接到完全错误的服务器
- **配置完备性检查**（步骤三第一动作）：管理面需凭据 + `HUAWEICLOUD_PROJECT_ID` + `SUPABASE_RDS_ENDPOINT`；frontend/OBS 需 AK/SK + `HUAWEICLOUD_REGION`。缺失项以清单**以清单形式提示用户填写**（不猜测不跳过）；endpoint 无法推导（discover 失败/非标准区域）→ 用户显式指定
- **边界外处置**：复杂业务逻辑（支付/第三方调用/长任务）超出 v1 数据层边界——明确告知用户并停止，不擅自以 RPC 模拟
- **Storage 按需接入**：步骤二识别文件/图片/视频管理诉求并标记 `storage` 能力 → 步骤三按**条件驱动**对接：**不无条件创建后端 OBS 桶**——仅当存储诉求存在**且**所选实例尚未对接时才创建（新建固定私有桶）；勾选已有应用且已对接 → **复用既有对接，不新建、不重复对接**；选既有桶必先通过桶策略安全评估（存在公开读/匿名授权即停止）；**禁止复用前端托管桶**（公开读桶复用即权限越界与隐私暴露）
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
| 步骤九 上线验证前 | references/launch-checklist.md | 三层清单与上线报告格式 |
| 每步骤完成前 | scripts/webapp-gate.py（check-stage；步骤五、六、七另跑 check-gate --number 3|4|5） | 🤖 断言机械核验，PASS 才算完成 |
| launched 之后的更新/回滚/下线/密钥轮换 | references/lifecycle.md | 生命周期工作流 |

一次会话的典型加载量：SKILL.md + project-state.md + workflow-stages.md 当前步骤小节 + 步骤强制门技能（如有）。routing-table.md 仅在路由不明时查询；不在早期步骤预加载 launch-checklist.md 与 lifecycle.md。

## 参考文档

- references/workflow-stages.md（步骤一–八 步骤 playbook；进入对应步骤前读）
- references/lifecycle.md（更新/回滚/下线/密钥轮换；launched 后读）
- references/project-state.md（webapp.json 契约；首次读写前读）
- references/routing-table.md（跨技能/MCP 路由矩阵；路由不明时查）
- references/launch-checklist.md（端到端上线清单；步骤九 验证前读）
- scripts/webapp-gate.py（步骤通过条件机械核验；每步骤完成前运行）
