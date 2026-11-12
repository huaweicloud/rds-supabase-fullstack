# RDS Supabase 管控 MCP Server（管理面）

> **语言切换：** [English](./README_en.md) | 中文

## 版本

0.4.0a1（开发预发行版，未完成六场景全量生产验收）

## 概述

华为云 RDS Supabase（自建 Supabase on RDS PostgreSQL）**全托管生命周期管理**的
MCP Server，属管理面（control plane）：应用创建、配置、安全访问、删除。通过原生
RDS 管理接口操作 Supabase 应用。SQL 与数据操作属独立数据面能力，见
`server/mcp_server_rds_supabase`；两台服务器分开交付，互不替换。

配套专项 Skill：`skills/huaweicloud-supabase/rds-supabase-mgr-mcp`（意图理解、
信息补齐、影响展示与确认指导）。深入使用说明见[用户指南](docs/USER_GUIDE.md)。

## 分类

数据库 / RDS Supabase 全托管生命周期（管理面）

## 功能

**应用查询**

- 查询当前项目的 Supabase 应用列表与详情
- 列出 RDS Supabase 管理 MCP 的可用能力范围（离线声明，不探测云状态）

**应用创建**

- 发现创建候选：可托管 PG 实例、Supabase 规格查询
- Single 模式创建提交（关联已有 PG 或按需新建 PG），两阶段确认

**应用删除**

- 删除 Supabase 应用（保留 PG，可能继续计费）；不级联删 PG

**访问控制**

- SSL 开关（开启需已核验的证书 ID）
- EIP 绑定/解绑
- 应用账号改密（经本地受保护请求引用，不收集明文）

**安全组（共享原生 RDS 入口）**

- 安全组与规则查询、创建组、指定 TCP 端口规则增删

**ApiKey**

- 元数据查询（六字段白名单，不含明文）
- 重置（强提示下游失效风险）
- 指定 Key 交付到受保护本地文件（不在对话输出明文）

**业务配置**

- 注册/匿名开关、Auth 提供方（GitHub/SMTP）、URL 与确认邮件模板、OBS 存储配置

**任务与执行账本**

- 任务状态查询与有界只读观察
- 本地执行计划检查/取消/对账；未知结果持久记录，禁止重放

**通用能力**

- 两阶段确认（confirm + plan_id 绑定参数、目标与凭据摘要）
- 云写开关默认关闭；共享核心只读拦截、保护名单、结构化审计与输出脱敏

## 工具清单

| 工具 | 场景 | 风险级别 | 说明 |
|---|---|---|---|
| `get_supabase_capabilities` | 列出 RDS Supabase 管理 MCP 的可用能力范围 | READ | 离线声明，不探测云状态 |
| `list_supabase_applications` | 分页查询当前项目所有 RDS Supabase 应用（支持排序过滤） | READ | type 固定 supabase；返回 total_count 与必备字段（名称/ID/公网IP/端口/规格/模式/创建时间，备注可空），嵌套对象脱敏透传 |
| `show_supabase_application` | 应用详情与状态 | READ | 状态非完成证明 |
| `list_supabase_api_keys` | ApiKey 元数据查询 | READ | 白名单输出，不含明文 |
| `reset_supabase_api_key` | ApiKey 重置（需确认） | DANGEROUS | 提交前按 ID 校验唯一 normal 记录 |
| `deliver_supabase_api_key` | 指定 Key 交付到本地文件（需确认） | DANGEROUS | 经 delivery_ref 别名 |
| `show_supabase_auth_config` | Auth 配置查询 | READ | 秘密排除 |
| `update_supabase_auth_flags` | 注册/匿名开关（需确认） | WRITE | 仅更新明确指定的布尔项 |
| `update_supabase_auth_config` | Auth 提供方/URL/模板（需确认） | WRITE | 经本地 request_ref |
| `update_supabase_storage` | OBS 存储配置（需确认） | WRITE | 首次启用需完整凭据 |
| `plan_supabase_creation` | 创建规划 | READ | planning_only，非执行方案 |
| `list_supabase_flavors` | Supabase 规格候选 | READ | creation_ready=false，非报价 |
| `list_supabase_manageable_instances` | 可托管 PG 查询 | READ | 同上 |
| `create_supabase_application` | Single 创建提交（需确认） | DANGEROUS | 经本地 request_ref；仅 Single 模式 |
| `delete_supabase_application` | 删除应用保留 PG（需确认） | DANGEROUS | 无级联删 PG |
| `change_supabase_ssl` | SSL 开关（需确认） | WRITE | 开启需证书 ID，关闭传 null |
| `plan_supabase_ssl` | SSL 切换规划 | READ | 证书步骤与缺口，无提交 |
| `change_supabase_eip` | EIP 绑定/解绑（需确认） | WRITE | 绑定需 ID+IPv4；解绑须省略绑定参数 |
| `change_supabase_application_password` | 应用改密（需确认） | DANGEROUS | 经本地 request_ref，不收集明文 |
| `list_supabase_security_groups` | 安全组列表 | READ | 共享原生 RDS 入口 |
| `show_supabase_security_group` | 安全组详情 | READ | |
| `create_supabase_security_group` | 创建安全组（需确认） | WRITE | 创建组不等于应用已可访问 |
| `add_supabase_security_group_rule` | 添加入站规则（需确认） | DANGEROUS | 指定 TCP 端口（默认 8443） |
| `delete_supabase_security_group_rule` | 删除规则（需确认） | DANGEROUS | |
| `show_supabase_job` | 任务状态查询 | READ | completion_verified=false |
| `wait_supabase_job` | 有界只读观察 | READ | 默认 3 次、最多 10 次 |
| `inspect_supabase_plan` | 本地计划检查 | READ | 不调用云 |
| `cancel_supabase_plan` | 取消未提交计划 | WRITE | 仅本地账本，幂等 |
| `reconcile_supabase_auth_plan` | Auth 计划对账 | WRITE | 云读 + 本地写，仅 Auth 开关场景 |

## 使用指引

### 前置条件

- Python 3.10+
- UV

**Linux/macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 安装

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-huaweicloud-rds-supabase-mgr          # stdio（默认）
uv run mcp-huaweicloud-rds-supabase-mgr -t streamable-http
```

`mcp-huaweicloud-rds-supabase-mgr` 为规范入口；旧入口 `mcp_server_supabase`
保留过渡，两者等价。

### 验证

```bash
uv run pytest                       # 80% 覆盖率门槛
uv run python tests/smoke_stdio.py
```

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

`discover` 联调 IAM 查询项目清单（REST 模式自查 Token 的项目作用域；sdk_core 模式列出
AK/SK 可见项目），按区域推导候选入口并列出 `suggested_env` 供勾选；显式配置的
`SUPABASE_RDS_ENDPOINT` 优先。探测可达不等于权限与生产验收。

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
| `SUPABASE_ENABLE_WRITES` | 否 | 云写开关；`true` 才能执行云侧写操作 | `false` |
| `HUAWEICLOUD_MCP_READ_ONLY` | 否 | `true` 拦截所有 WRITE/DANGEROUS 工具 | `false` |
| `SUPABASE_STATE_FILE` | 否 | 本地执行账本（SQLite）路径；跨重启保持同一账本 | 用户本地状态目录 |
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
- **执行账本**：SQLite 本地账本记录计划、任务与状态。提交超时或结果未知时先
  `inspect_supabase_plan`；`submitted`/`accepted`/`unknown` 均不得自行重放，
  禁止删除账本绕过保护。
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

### uvx 运行（git 仓库版本）

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
                "SUPABASE_RDS_ENDPOINT": "",
                "HUAWEICLOUD_PROJECT_ID": "",
                "HUAWEICLOUD_AUTH_TOKEN": "",
                "HUAWEICLOUD_MCP_READ_ONLY": "true",
                "SUPABASE_ENABLE_WRITES": "false"
            }
        }
    }
}
```

sdk_core 模式（AK/SK）示例见 [examples/mcp-sdk.example.json](examples/mcp-sdk.example.json)。

## 示例

### Cursor / Claude Desktop / Trae

将上述 JSON 配置填入 MCP 客户端并填入凭证（首次接入保持只读），然后自然语言使用：

- "查询当前 MCP 支持哪些 Supabase 场景" → `get_supabase_capabilities()`
- "列出当前项目的 Supabase 应用" → `list_supabase_applications()`
- "查应用 app-123 的详细状态" → `show_supabase_application(application_id="app-123")`
- "列出应用 app-123 的 ApiKey 类型和状态，不看值" → `list_supabase_api_keys(application_id="app-123")`
- "预览为应用 app-123 关闭 SSL，暂不执行" → `change_supabase_ssl(application_id="app-123", enable_ssl=false)`（`confirm=false` 返回计划与 `plan_id`）
- "确认执行刚才预览的 SSL 变更" → 相同参数 `confirm=true` + `plan_id`
- "列出可托管的 PG 实例" → `list_supabase_manageable_instances()`
- "删除应用 app-123，先说明影响" → `delete_supabase_application(...)`（先预览确认；仅删应用保留 PG）
- "查任务 job-456 的状态" → `show_supabase_job(job_id="job-456")`

## 深入文档

- [用户指南](docs/USER_GUIDE.md)——安装、验证与自然语言操作全流程
- [工具契约](docs/TOOL_CONTRACTS.md)——输入输出与确认语义的权威定义
- [恢复规则](docs/RECOVERY.md)、[对账契约](docs/RECONCILIATION.md)——异常分流与 Auth 对账
- [本地秘密输入输出](docs/LOCAL_REQUESTS.md)——敏感请求引用机制
- [SDK 模式](docs/SDK.md)、[迁移说明](docs/MIGRATION.md)
- [docs/legacy/](docs/legacy/)——已归档的 Windows 离线交付流程

## 许可证

MIT
