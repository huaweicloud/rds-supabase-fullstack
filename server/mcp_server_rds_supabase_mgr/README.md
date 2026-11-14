# RDS Supabase 管理 MCP Server

> **语言切换：** [English](./README_en.md) | 中文

## 版本

0.4.0a18（开发预发行版）；Python `3.10+`；MCP Python SDK `2.x`；31 个工具。

## 概述

该服务把华为云 RDS Supabase（自建 Supabase on RDS PostgreSQL）的管理 API 封装为
MCP 工具，覆盖应用的创建、配置、公网访问开通、变更与删除。属管理面
（control plane）：通过原生 RDS 管理接口操作 Supabase 应用；SQL 与数据操作属独立
数据面服务，见 `server/mcp_server_rds_supabase`，两台服务器分开交付，互不替换。

安全组操作经 KooCLI 通道执行（见[安全组与 KooCLI 通道](#安全组与-koocli-通道)）。

配套专项 Skill：`skills/huaweicloud-supabase/rds-supabase-mgr-mcp`（意图理解、
信息补齐、影响展示与确认指导）。

## 快速开始

准备 Python 3.10+、[uv](https://docs.astral.sh/uv/)、华为云凭证（AK/SK 或服务
Token）。首次接入保持只读：

```bash
export HUAWEICLOUD_MCP_READ_ONLY="true"
uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" \
  mcp-huaweicloud-rds-supabase-mgr
```

通用 stdio 客户端配置（Token 模式；AK/SK 模式见
[examples/mcp-sdk.example.json](examples/mcp-sdk.example.json)）：

```json
{
  "mcpServers": {
    "rds-supabase-mgr-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr",
        "mcp-huaweicloud-rds-supabase-mgr"
      ],
      "env": {
        "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 端点>",
        "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
        "HUAWEICLOUD_AUTH_TOKEN": "<服务 Token>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

连接后调用 `list_supabase_applications` 验证端点、权限与项目。完整安装方式、
凭据模式与安全组前置条件见后文。

## 分类

数据库 / 云资源管理 / 运维自动化（RDS Supabase 生命周期，管理面）。

## 功能

**应用查询**

- 应用列表：分页、过滤、排序
- 应用详情：基础配置（名称、模式、状态）、规格配置（规格、节点）、安全配置（SSL）、
  网络配置（公网/内网 IP、端口）、存储配置（OBS 桶对接）
- 管理能力清单：声明本服务的管理范围与职责边界，明确哪些操作由本服务执行、
  哪些由用户经控制台完成

**应用创建**

- 创建前分析业务场景和使用方式，逐项拆解，输出每个场景要准备什么、
  怎么做：
  - **托管数据库实例**：新建实例，或关联已有实例
  - **OBS 存储对接**：有图片、视频、大文件存储需求时使用
  - **EIP 绑定**：需要公网访问时使用
  - **SSL 对接**：高安全要求场景；需先购买 CCM 证书
- 应用规格列表查询：默认查单机模式可用规格；主备 Ha 版规格是否可用，
  以局点实时查询为准
- 可托管 PostgreSQL 实例查询——关联已有实例场景
- 数据库实例规格查询——同时新建实例场景（经 KooCLI）
- 周边依赖自动发现：VPC、子网、可用区、安全组、OBS 桶等依赖资源的列表与详情配置
  （使用 KooCLI 功能探索）
- 创建提交：Single/Ha、按需/包周期，两阶段确认；包周期返回订单，控制台支付

**应用删除**

- 删除应用，保留 PG（不级联删除）
- 删除托管 PG 实例：双标识 + 托管绑定 + 共享引用 + 删前实读四层校验；仅限按需计费

**访问控制**

- SSL 启用与关闭（启用需购买 CCM 证书）
- 弹性公网 IP 绑定与解除（控制公网访问）
- 应用改密（经本地受保护请求引用，不收集明文）

**安全组配置（KooCLI 通道）**

- 安全组列表与详情查询
- 创建安全组，匹配应用要求
- 删除应用安全组
- 新增或删除出/入方向的访问规则

**应用接入 API Key**

- API Key 列表查询：按用途过滤——`publishable`（客户端公开发布）、`secret`（服务端保密）、
  `anon`（匿名访问）、`service_role`（服务端管理员）
- 重置指定 API Key：应对密钥泄露与滥用风险
- 查询 API Key 密钥值：不在对话中直接展示，写入本地受保护文件，防止隐私泄露

**业务配置**

- 注册/匿名开关、Auth 提供方（GitHub/SMTP）、URL 与邮件模板、OBS 存储

**任务状态跟踪**

- 查询下发任务的状态
- 在超时时间范围内轮询任务状态至终态，用于等待任务完成

**本地执行记录**

- 计划检查/取消/核对；结果未知持久记录，禁止重放

**通用能力**

- 两阶段确认（confirm + plan_id 绑定参数、目标与凭据摘要）
- 云写开关默认关闭；只读拦截、保护名单、结构化审计、输出脱敏

## 可用工具

| 工具 | 场景 | 风险 |
|---|---|---|
| `get_supabase_capabilities` | 列出管理能力范围 | READ |
| `list_supabase_applications` | 分页查询应用（支持排序过滤） | READ |
| `show_supabase_application` | 查询应用详情（状态/SSL/IP 等） | READ |
| `list_supabase_api_keys` | API Key 元数据（无 value 值） | READ |
| `reset_supabase_api_key` | ApiKey 重置（需确认） | DANGEROUS |
| `deliver_supabase_api_key` | 指定 Key 交付到本地文件（需确认） | DANGEROUS |
| `show_supabase_auth_config` | 查询 Auth 认证配置 | READ |
| `update_supabase_auth_flags` | 注册/匿名开关（需确认） | WRITE |
| `update_supabase_auth_config` | Auth 提供方/URL/模板（需确认，经 request_ref） | WRITE |
| `update_supabase_storage` | OBS 存储配置（需确认） | WRITE |
| `plan_supabase_creation` | 创建规划（意图驱动，非执行） | READ |
| `list_supabase_flavors` | Supabase 规格候选 | READ |
| `list_supabase_manageable_instances` | 可托管 PG 查询 | READ |
| `create_supabase_application` | 创建提交（需确认，经 request_ref） | DANGEROUS |
| `delete_supabase_application` | 删除应用保留 PG（需确认） | DANGEROUS |
| `delete_supabase_managed_instance` | 删除应用托管的 PG 实例（需确认；校验托管绑定且无其他应用引用，仅按需计费） | DANGEROUS |
| `change_supabase_ssl` | SSL 开关（需确认） | WRITE |
| `plan_supabase_ssl` | SSL 切换规划 | READ |
| `change_supabase_eip` | EIP 绑定/解绑（需确认） | WRITE |
| `change_supabase_application_password` | 应用改密（需确认，经 request_ref） | DANGEROUS |
| `list_supabase_security_groups` | 安全组列表 | READ |
| `show_supabase_security_group` | 安全组详情及规则 | READ |
| `create_supabase_security_group` | 创建安全组（需确认） | WRITE |
| `add_supabase_security_group_rule` | 加单条规则（需确认；入/出方向，TCP/UDP） | DANGEROUS |
| `delete_supabase_security_group_rule` | 删单条规则（需确认，校验所有权） | DANGEROUS |
| `delete_supabase_security_group` | 删除整组（需确认，删前核对无引用） | DANGEROUS |
| `show_supabase_job` | 任务状态查询 | READ |
| `wait_supabase_job` | 有界只读观察 | READ |
| `inspect_supabase_plan` | 本地计划检查 | READ |
| `cancel_supabase_plan` | 取消未提交计划 | WRITE |
| `reconcile_supabase_auth_plan` | Auth 计划核对 | WRITE |

所有 READ 工具随时可用；WRITE/DANGEROUS 工具受两阶段确认与环境开关约束
（见[安全机制](#安全机制)）。

## 安全组与 KooCLI 通道

安全组六个工具不经过 RDS 服务端点：原生 RDS 入口不代理 VPC API，直调必然失败。
它们通过本机 KooCLI（`hcloud`）执行，调用 VPC v3 操作
（`CreateSecurityGroup/v3`、`CreateSecurityGroupRule/v3` 等）。

- **KooCLI 前置条件**：本机需安装 hcloud 并接受首次运行隐私协议。安装方法见
  技能 [INSTALL.md 第四节](../../skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md)。
- **二进制定位**：`HCLOUD_BIN` 环境变量 → 固定安装目录 → PATH，每次调用重新定位，
  安装后无需重启会话。
- **凭据注入**：`HUAWEICLOUD_ACCESS_KEY`/`HUAWEICLOUD_SECRET_KEY` 同时存在时按命令
  注入；否则回落 hcloud profile。**REST Token 模式下需本机配置 hcloud profile**
  （`hcloud configure init`），否则安全组工具报凭据缺失。
- **区域与项目**：区域取 `HUAWEICLOUD_REGION`，缺省时从 `SUPABASE_RDS_ENDPOINT`
  域名推导；项目由 KooCLI 按区域默认项目解析，子项目账号须在 hcloud profile 配置
  `--cli-project-id`。
- **错误透传**：VPC 后端 error_code/error_msg/request_id 原样透传；隐私协议未接受、
  二进制缺失、超时各有专用错误码与处置指引。

## 使用指南

### 前置条件

1. Python 3.10+；使用 uvx 时安装 [uv](https://docs.astral.sh/uv/)。
2. 具有所需最小权限的华为云凭证（见[权限建议](#权限建议)）。
3. 使用安全组工具时：本机安装 KooCLI 并完成隐私协议（见上一节）。

### 安装

**uvx 直接运行（推荐，git 仓库唯一规范来源）：**

```bash
uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" \
  mcp-huaweicloud-rds-supabase-mgr
```

服务未发布到 PyPI；PyPI 上的同名第三方包不是本服务，禁止安装。

**克隆开发：**

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-huaweicloud-rds-supabase-mgr          # stdio（默认）
uv run mcp-huaweicloud-rds-supabase-mgr -t streamable-http
```

`mcp-huaweicloud-rds-supabase-mgr` 为规范入口；旧入口 `mcp_server_supabase`
保留过渡，两者等价。慢网络下 uvx 启动超时的处置见
[技能安装手册](../../skills/huaweicloud-supabase/rds-supabase-mgr-mcp/references/install.md)。

### 诊断 CLI

```bash
uv run python -m mcp_server_supabase.diagnostics check       # 只检查配置格式与依赖
uv run python -m mcp_server_supabase.diagnostics offline     # 离线 stdio 自检
# 从凭据自动发现项目与候选 RDS 入口（REST token 或 AK/SK 二选一）：
uv run python -m mcp_server_supabase.diagnostics discover
uv run python -m mcp_server_supabase.diagnostics discover --probe   # 追加只读可达性探测
# 仅在已授权测试环境执行真实只读检查：
uv run python -m mcp_server_supabase.diagnostics readonly --allow-cloud-read
```

`discover` 联调 IAM 查询项目清单，按区域推导候选入口并列出 `suggested_env`
供勾选；显式配置的 `SUPABASE_RDS_ENDPOINT` 优先。探测可达不等于权限与生产验收。
诊断 CLI 不提交云写操作，摘要不含资源值与凭据。

## 配置

### 环境变量

凭据模式二选一：**REST token 模式**（默认，`HUAWEICLOUD_AUTH_TOKEN`）或
**sdk_core 模式**（`SUPABASE_TRANSPORT=sdk_core` + AK/SK）。凭据经可信宿主环境
注入，不作为工具参数。

| 变量 | 必填 | 说明 | 默认值 |
|---|---|---|---|
| `SUPABASE_RDS_ENDPOINT` | 是 | 原生 RDS HTTPS 服务入口（不含路径/查询/用户信息；非 Console 或 /rest 代理）。可由 `diagnostics discover` 从凭据推导生成 | - |
| `HUAWEICLOUD_PROJECT_ID` | 是 | 目标项目 ID（与局点一致） | - |
| `HUAWEICLOUD_AUTH_TOKEN` | REST 模式必填 | 外部预置的服务 Token，每次请求读取 | - |
| `SUPABASE_TRANSPORT` | 否 | 设为 `sdk_core` 启用华为 SDK Core 签名模式 | REST token |
| `HUAWEICLOUD_ACCESS_KEY` | sdk_core 模式必填 | 账号 AK | - |
| `HUAWEICLOUD_SECRET_KEY` | sdk_core 模式必填 | 账号 SK | - |
| `HUAWEICLOUD_SECURITY_TOKEN` | 否 | STS 临时凭据 token | - |
| `HUAWEICLOUD_REGION` | 否 | 安全组 KooCLI 通道区域；缺省从 `SUPABASE_RDS_ENDPOINT` 域名推导 | 推导 |
| `HCLOUD_BIN` | 否 | KooCLI 二进制路径覆盖（固定目录与 PATH 之外的显式指定） | 自动定位 |
| `SUPABASE_ENABLE_WRITES` | 否 | 云写开关；`true` 才能执行云侧写操作 | `false` |
| `HUAWEICLOUD_MCP_READ_ONLY` | 否 | `true` 拦截所有 WRITE/DANGEROUS 工具 | `false` |
| `SUPABASE_STATE_FILE` | 否 | 本地执行记录（SQLite）路径；跨重启保持同一记录 | 用户本地状态目录 |
| `SUPABASE_REQUESTS_FILE` | 否 | 敏感请求本地引用注册表（操作方预置） | - |
| `REQUESTS_CA_BUNDLE` | 否 | 自定义可信 CA（PEM 文件） | - |
| `HUAWEICLOUD_MCP_PROTECTED_IDS` | 否 | 护栏：受保护资源 ID（逗号分隔，命中即 block） | 空 |
| `HUAWEICLOUD_MCP_PROTECTED_NAMES` | 否 | 护栏：受保护资源名称（逗号分隔，命中即 block） | 空 |
| `HUAWEICLOUD_MCP_PROTECTED_TAGS` | 否 | 护栏：受保护标签（逗号分隔 `k` 或 `k=v`） | 空 |
| `HUAWEICLOUD_MCP_GUARDRAILS_CONFIG` | 否 | 复杂规则文件 `guardrails.yaml` 路径 | 空 |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | 否 | 审计 JSONL 文件路径（审计始终开启，默认写 stderr） | 空 |
| `MCP_SERVER_PORT` | 否 | streamable-http 端口 | `8000` |
| `MCP_SERVER_HOST` | 否 | streamable-http 绑定地址 | `0.0.0.0` |

### 安全机制

- **两阶段确认**：写工具默认 `confirm=false` 持久化十分钟计划并返回 `plan_id`；
  确认后以**相同参数** `confirm=true` + `plan_id` 提交。参数、项目、服务地址或
  凭据变更须重新预览确认。
- **本地执行记录**：SQLite 记录计划、任务与状态。提交超时或结果未知时先
  `inspect_supabase_plan`；`submitted`/`accepted`/`unknown` 均不得自行重放，
  禁止删除记录绕过保护。
- **敏感请求本地引用**：改密、SMTP、GitHub、OBS 凭据经操作方预置的本地注册表
  （`SUPABASE_REQUESTS_FILE`）以别名提供；工具不接受明文，不读取交付文件内容。
- **202 只表示受理**：任务 `completed` 不等于业务验证完成，须回查资源。
- **写权限分层**：云写开关（`SUPABASE_ENABLE_WRITES`，默认关闭）与共享核心
  只读拦截（`HUAWEICLOUD_MCP_READ_ONLY`）独立生效，均不可由 Agent 自行修改。

**护栏已知局限（参数级匹配）：** 保护规则匹配工具参数中的资源 ID、名称类参数。
仅云侧配置而参数中未出现的保护属性无法命中；建议通过环境变量或 `guardrails.yaml`
主动配置保护名单。

`guardrails.yaml` 示例：

```yaml
version: 1
rules:
  - id: protect-prod-supabase
    match:
      tools: ["delete_supabase_application"]
      risks: [DANGEROUS]
      resources:
        name_patterns: ["^prod-"]
    action: block
    message: 生产 Supabase 应用受保护，请联系运维。
```

## 示例

### 工作流一：从零创建一个能访问的应用

1. 调用 `plan_supabase_creation`，按意图（数据库路线/存储/公网/SSL）取得阶段化
   准备方案与必供字段清单。
2. 按方案准备：安全组（`create_supabase_security_group` 建专用组，
   `add_supabase_security_group_rule` 配 8443 入方向与 5432 出方向）、本地请求
   文件（含 root 密码、存储凭据等秘密）。
3. `create_supabase_application(request_ref, confirm=false)` 预览 → 把脱敏参数
   给用户核对 → 相同参数 `confirm=true` + `plan_id` 提交。
4. 用返回的 `job_id` 调用 `show_supabase_job`（或 `wait_supabase_job` 有界等待）
   到终态。
5. 回查 `show_supabase_application`：公网 IP 未绑定时先 `change_supabase_eip`，
   再以 `list_supabase_api_keys` + `deliver_supabase_api_key` 交付接入信息。

### 工作流二：给应用开安全组端口

1. `create_supabase_security_group` 预览 → 确认，创建带用途描述的专用组。
2. `add_supabase_security_group_rule` 加 8443 入方向（来源网段）与 5432 出方向
   （`direction='egress'`），各自预览 → 确认。
3. `show_supabase_security_group` 回读规则，核对方向与端口。
4. 需要收回时 `delete_supabase_security_group_rule`（先核对该组未被共用）；
   整组下线走 `delete_supabase_security_group`（删前核对无实例/NIC 引用）。

所有写接口都可能异步执行。MCP 调用成功只表示云 API 已受理，不表示资源变更已经
完成。

## 客户端兼容性

| 客户端 | 接入方式 | 说明 |
|---|---|---|
| opencode | stdio | 项目级 `opencode.json`，`mcp.servers.*` 结构；保存即自动连接 |
| Claude Code | stdio | 项目级 `.mcp.json`；会话内批准一次即连 |
| Claude Desktop / Cursor / Trae | stdio | `command`/`args`/`env` 配置 |
| CodeArts | stdio | 项目级 `mcp_settings.json`（设置 → MCP 工具）；改既有条目需手动重启 |
| 远程模式 | Streamable HTTP | `mcp-huaweicloud-rds-supabase-mgr -t streamable-http`，端点 `/mcp`；生产部署应前置网关配置 HTTPS 与鉴权 |

不提供旧版 SSE 传输。

## 权限建议

- **只读发现**：RDS 应用/规格/可托管实例查询 + IAM 项目查询；创建选型所需的
  VPC、子网、可用区、EIP 查询经 KooCLI，权限随 KooCLI profile。
- **写操作**：只增加实际启用工具对应的 RDS 应用创建/变更权限与 VPC 安全组写权限。
- **危险操作**：删除类、改密、Key 重置建议使用单独身份或临时授权，并配合
  `HUAWEICLOUD_MCP_PROTECTED_*` 保护名单与确认规则。
- 不要为方便而把长期管理员凭证配置到 MCP 客户端；生产环境建议使用临时安全凭证。

## 开发、测试和验证

```bash
uv sync --all-groups
uv run ruff check src tests
uv run pytest                       # 默认不访问云上资源，80% 覆盖率门槛
uv run python tests/smoke_stdio.py  # 离线 stdio 冒烟
```

Live 验证只能在专用测试账号中显式启用；创建计费资源时必须在失败路径也执行清理，
并确认删除任务到达终态。发布前检查 wheel 元数据、全新 Python 3.10 环境安装与
MCP 工具列表。

## 贡献和支持

贡献流程、安全报告方式与版本变更见仓库根目录 `CONTRIBUTING.md`、`SECURITY.md`
与 `CHANGELOG.md`。普通问题使用 GitHub Issue；凭证泄露和安全问题不得提交到公开
Issue。

## 深入文档

- [用户指南](docs/USER_GUIDE.md)——安装、验证与自然语言操作全流程
- [工具契约](docs/TOOL_CONTRACTS.md)——输入输出与确认语义的权威定义
- [恢复规则](docs/RECOVERY.md)、[核对契约](docs/RECONCILIATION.md)——异常分流与 Auth 计划核对
- [本地秘密输入输出](docs/LOCAL_REQUESTS.md)——敏感请求引用机制
- [SDK 模式](docs/SDK.md)、[迁移说明](docs/MIGRATION.md)
- [docs/legacy/](docs/legacy/)——已归档的 Windows 离线交付流程

## 许可证

MIT
