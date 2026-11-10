# RDS Supabase 管控 MCP + Skill 用户指南

适用版本：0.3.8a2开发预发行版。文档更新：2026-11-09。

本工具让你在 Claude Code 等支持本地 MCP 的助手中，用自然语言查询和管理华为云 RDS Supabase（全托管生命周期：应用创建、配置、安全访问、删除）。MCP 负责调用云接口，专项 Skill 负责理解需求、补充信息、展示影响及指导确认。安装采用本仓统一的 uvx 模板，跨平台（macOS / Linux / Windows）。先完成本地接入，再验证真实云访问；当前开发版尚未完成生产发布验收。

## 1. 能做什么

| 场景 | 当前支持 |
|---|---|
| 创建应用 | 查询候选；Single模式关联已有PG或按需新建PG |
| 删除应用 | 删除Supabase应用，保留PG；PG可能继续计费 |
| 访问控制 | 已有EIP绑定/解绑、SSL开关、应用账号改密 |
| 安全组 | 查询、创建、指定TCP端口规则增删 |
| ApiKey | 元数据查询、重置、指定Key交付到受保护本地文件 |
| 业务配置 | 注册开关、Auth URL、GitHub、SMTP、确认邮件模板和OBS |

暂不支持Ha、包周期创建、应用删除级联PG、自动购买证书或EIP、修改EIP带宽。SQL和数据操作属于独立数据面能力（server/mcp_server_rds_supabase 与 rds-supabase-mcp 技能）。证书由用户在外部流程准备；共享安全组影响需先核对。

## 2. 前置条件

- 已安装 uv（含 uvx）：macOS/Linux 执行 `curl -LsSf https://astral.sh/uv/install.sh | sh`；Windows PowerShell 执行 `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- 已安装支持本地 MCP 的客户端（如 Claude Code），并能正常与所配置的模型对话；本包不安装客户端或配置模型账号
- 机器可访问 github.com（uvx 首次运行需拉取本仓库）。完全离线或 Windows 离线交付场景见 [docs/legacy/](legacy/)（已归档的 bundle 流程）

## 3. 安装（uvx 模板）

由操作方在可信本地环境填入凭据后，将以下配置加入 MCP 客户端（REST token 模式）：

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
        "SUPABASE_RDS_ENDPOINT": "<原生 RDS HTTPS 入口>",
        "HUAWEICLOUD_PROJECT_ID": "<项目 ID>",
        "HUAWEICLOUD_AUTH_TOKEN": "<服务 Token>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

SDK 签名模式（AK/SK）见 [examples/mcp-sdk.example.json](../examples/mcp-sdk.example.json)：设置 `"SUPABASE_TRANSPORT": "sdk_core"`，改用 `HUAWEICLOUD_ACCESS_KEY` / `HUAWEICLOUD_SECRET_KEY`（临时凭据另加 `HUAWEICLOUD_SECURITY_TOKEN`）。

入口与项目 ID 可在配置前自动发现：`uv run python -m mcp_server_supabase.diagnostics discover` 用现有凭据查询 IAM 项目清单（REST 模式自查 Token 作用域）并按区域推导候选入口，输出 `suggested_env` 供勾选；追加 `--probe` 做一次只读可达性探测。显式配置的 `SUPABASE_RDS_ENDPOINT` 优先。安全组工具与 RDS 共用同一原生入口，无需单独配置。

首次接入建议保持只读（上表默认值）。uvx 首次运行解析依赖并缓存，之后启动为秒级；需要更新到仓库最新版本时在命令中加入 `--refresh`。旧入口脚本名 `mcp_server_supabase` 与规范入口 `mcp-huaweicloud-rds-supabase-mgr` 等价，保留过渡。

## 4. 安装专项 Skill

技能位于本仓 `skills/huaweicloud-supabase/rds-supabase-mgr-mcp/`。将该目录复制到客户端技能位置（项目级 `.claude/skills/` 或用户级技能目录），或使用 `npx skills add` 安装。确认最终存在 `rds-supabase-mgr-mcp/SKILL.md` 与完整 references 目录；已有同名 Skill 时先核对版本，不反复复制嵌套目录。使用的是本专项 Skill，不是 huaweicloud-mcp-dev 开发 Skill。

## 5. 验证

重载客户端后输入 `/mcp` 检查连接；实际工具列表应包含 29 个工具。输入 `/rds-supabase-mgr-mcp` 明确加载专项 Skill，再输入：

> 查询当前MCP能力，说明支持哪些Supabase场景；本次不访问云资源。

这一步验证自然语言、Skill 和工具连接，不需要云凭据。Skill 不是鉴权机制，不能因其加载成功就宣称云服务可用。客户端版本不同，具体提示界面可能不同；以实际工具列表和调用结果为准。

需要诊断 CLI 时使用源码检出：

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run python -m mcp_server_supabase.diagnostics check       # 只检查配置格式与依赖，不联网
uv run python -m mcp_server_supabase.diagnostics offline     # 离线 stdio 自检
# 仅在已授权测试环境执行真实只读检查：
uv run python -m mcp_server_supabase.diagnostics readonly --allow-cloud-read
```

诊断摘要不含资源响应值与凭据，成功读取不等于任务完成。CLI 所需模式变量须与客户端配置一致（bash：`export SUPABASE_TRANSPORT=sdk_core HUAWEICLOUD_MCP_READ_ONLY=true SUPABASE_ENABLE_WRITES=false`；PowerShell 用 `$env:` 同名设置）。

## 6. 配置真实云访问

由用户在可信本地环境向客户端启动进程提供下列变量，不发送到聊天、不写入项目或公开仓库：

| 配置 | 用途 |
|---|---|
| SUPABASE_RDS_ENDPOINT | 当前局点的原生RDS HTTPS入口，不是Console地址或/rest代理；可由 `diagnostics discover` 从凭据推导 |
| HUAWEICLOUD_PROJECT_ID | 与局点一致的项目ID；可由 `diagnostics discover` 查询勾选 |
| HUAWEICLOUD_ACCESS_KEY、HUAWEICLOUD_SECRET_KEY | 具备所需权限的AK/SK |
| HUAWEICLOUD_SECURITY_TOKEN | 仅临时凭据时使用匹配的STS token |
| REQUESTS_CA_BUNDLE | 需要自定义CA时指定可信本地PEM文件 |

入口、IAM权限及API开放情况以实际局点为准。不要把浏览器可登录Console等同于Python SDK能够访问。MCP子进程必须继承配置；更新后重启客户端。模型服务代理和云API网络分开处理，不统一设置全局NO_PROXY=*，不关闭TLS验证。SDK模式仅设置SSL_CERT_FILE不能保证采用该CA。

## 7. 用自然语言操作

先保持只读，逐条尝试：

| 用户输入 | 应有行为 |
|---|---|
| 列出当前项目的Supabase应用，不做修改 | 查询应用并说明分页范围 |
| 查询应用〈ID〉的EIP绑定情况，解释解绑影响 | 查询详情，不提交解绑 |
| 我要创建Ha模式应用，先检查是否支持 | 明确不支持，不擅自改成Single |
| 我想用已有PG创建Single应用，先说明需要哪些信息 | 查询/澄清配置，不索取聊天明文密码 |
| 列出应用〈ID〉的ApiKey类型和状态，不查看值 | 仅元数据查询 |
| 我想开放8443，但还没确定来源，先别改 | 澄清来源和共享影响，不默认全网放行 |

需要真实修改时，先选择允许变更的隔离测试资源。由操作方将该MCP配置改为 `HUAWEICLOUD_MCP_READ_ONLY=false` 和 `SUPABASE_ENABLE_WRITES=true` 并重启。Agent不得自行修改权限配置。权限开启后仍必须预览并确认具体变更。

例如EIP解绑对话：

1. "为应用〈ID〉预览解绑EIP，暂不执行。"
2. 核对目标、原绑定、服务中断及费用说明。
3. "确认执行刚才预览的解绑，仅限这个应用。"
4. 要求查询任务、回查应用；实际公网连通由测试人员验证。
5. 需要恢复时，用原EIP ID和地址生成新计划，再确认恢复。

202只表示受理，任务completed不等于业务验证完成。提交超时先查计划/任务/资源，不重复提交。取消未提交计划不等于取消已提交云任务。测试结束后恢复只读并重启。

密码、SMTP、OAuth及OBS秘密由可信操作方通过本地引用提供；ApiKey只交付到受保护文件，不让Agent读取内容。详见[本地秘密输入输出](LOCAL_REQUESTS.md)。文件权限（含 Windows ACL）需操作方设置；此机制不是宿主秘密保险库。

## 8. 版本与测试背景

本地基线：124 项 pytest 通过、覆盖率 93.09%（0.3.8a2，含 stdio 子进程），保留 80% 门槛。0.3.6a1 历史真云结果与 0.3.8a1 Windows 工作站记录见 [docs/legacy/](legacy/) 各 RELEASE 与 WORKSTATION 文档；六场景实现范围见[六场景矩阵](SIX_SCENARIO_MATRIX.md)。

旧版本接口通过不代表本版全部29工具、全部六场景或全部模型都已通过。当前SDK Core负责签名和传输，尚未接入正式生成式Supabase产品SDK。依赖安全策略、可信CA/代理、真实新增场景、Agent轨迹和码道联合验收仍有待完成项。当前版本面向开发验证，不建议直接用于生产。

## 9. 常见问题

| 现象 | 处理 |
|---|---|
| uvx 拉取失败 | 检查 github.com 网络与代理；或改用源码安装（uv sync） |
| MCP连接失败 | 检查客户端配置、uvx 输出与进程日志，不先修改云权限 |
| 工具数量/版本不符 | 检查是否启动了旧环境并重启客户端 |
| Skill未加载 | 检查技能目录、SKILL.md路径及references，显式调用专项Skill |
| 入口/项目检查失败 | 检查原生入口及局点项目对应关系 |
| TLS失败 | 配置可信CA；缺CA记录阻塞，不关TLS |
| 代理504 | 确认云目标是否应直连及进程代理；保持模型服务代理可用 |
| 只读阻止修改 | 由操作方确认测试范围再配置写权限，Agent不能绕过 |
| 修改结果未知 | inspect计划、查任务/资源；不要删除账本或重新提交 |

需要反馈时提供版本、阶段、用例、脱敏错误类别和任务/资源/业务结论，不提供凭据或完整抓包。完整范围见[六场景矩阵](SIX_SCENARIO_MATRIX.md)，联调执行单见[legacy/NEXT_WORKSTATION_PROMPT.md](legacy/NEXT_WORKSTATION_PROMPT.md)。
