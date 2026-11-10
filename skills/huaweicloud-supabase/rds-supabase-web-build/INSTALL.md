# rds-supabase-web-build 一键安装指导（自然语言动态安装）

面向想用一句话创建并托管 RDS Supabase Web 应用的用户。**使用方式：把本文档交给你的
AI Agent，对它说：**

> 按 INSTALL.md 安装 rds-supabase-web-build 技能及其依赖，装完告诉我怎么触发。

Agent 按下述步骤执行即可；人类也可照读自查。安装本身**不需要**任何云资源先行就绪。

## 安装什么、不装什么（动态安装的三层结构）

| 层 | 何时安装 | 方式 |
|---|---|---|
| 技能文件（6 个） | 现在，一次性 | `npx skills add` 或复制目录到 Agent 技能目录 |
| 管理面 MCP（29 工具） | 现在，一次性 | uvx 模板 + 凭据注入（devkit 优先 / discover 勾选） |
| 数据面 MCP（38 工具） | **刻意不装** | 实例在 ① 阶段才创建；② 阶段由技能按 rds-supabase-mcp 技能 `references/install.md` 动态安装 |

数据面 MCP 依赖实例网关 URL 与 API Key——安装时实例尚不存在。这正是"动态"的本体：
不要现在向用户索取这三项信息，也不要预置占位配置。

## 前置条件

| 项 | 要求 | 说明 |
|---|---|---|
| AI Agent | 支持 MCP 与 Agent Skills 标准 | opencode / Claude Code / Cursor 等 |
| uv | ≥ 0.5（含 uvx） | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | ≥ 3.10 | uvx 自动管理，本机仅在本地运行时需要 |
| 网络 | 可达 GitHub 与 PyPI | 内网环境见"常见问题"镜像方案 |
| 凭据（二选一） | devkit 已登录，或 AK/SK、服务 Token | 放**受保护文件**（0600），不在对话中出现 |
| npm（可选） | Node ≥ 18 | 仅 `npx skills add` 需要；无则手动复制 |

## 一句话安装

用户对 Agent 说：

> 按 INSTALL.md 安装 rds-supabase-web-build 技能及其依赖，装完告诉我怎么触发。

Agent 执行以下 5 步。

### 第 1 步：安装技能文件

方式 A（Agent Skills 开放标准，推荐）：

```bash
npx skills add huaweicloud/rds-supabase-fullstack
```

方式 B（手动复制）：克隆仓库，把 `skills/huaweicloud-supabase/` 下六个技能目录复制到
Agent 技能目录（opencode：`~/.config/opencode/skills/`；Claude Code：`~/.claude/skills/`；
其余宿主按其技能机制，Agent 自知位置）：

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack
cp -r rds-supabase-fullstack/skills/huaweicloud-supabase/* <你的技能目录>/
```

安装的六个技能：`rds-supabase-web-build`（编排总指挥）、`rds-supabase-mgr-mcp`、
`rds-supabase-mcp`、`rds-supabase-usage`、`rds-supabase-frontend`、
`rds-supabase-postgres-best-practices`。

校验：每个目录含 `SKILL.md`；克隆了仓库的，可运行
`uv run --directory server/mcp_server_rds_supabase python ../../scripts/validate_skills.py`，
期望输出 `validate-skills: OK (7 skills)`。

### MCP 项目地址与安装方式（只允许本仓来源）

| MCP | 仓内路径 | 入口脚本 | git uvx 模板 | 本地克隆运行 |
|---|---|---|---|---|
| 管理面 `rds-supabase-mgr` | `server/mcp_server_rds_supabase_mgr` | `mcp-huaweicloud-rds-supabase-mgr` | `uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr` | `uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr` |
| 数据面 `rds-supabase` | `server/mcp_server_rds_supabase` | `mcp-server-huaweicloud-rds-supabase` | `uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`（② 阶段动态装） | `uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase` |

> **警示（Agent 必读）**：PyPI 与应用市场存在**同名/相似的第三方 "supabase" MCP 包**——它们不是本项目的服务器。除上表两种来源（git uvx 模板 / 本仓本地路径）外，**不得搜索、安装或引入任何其他来源的 MCP**；发现已配置了其他来源时，先移除再按本表重装。

### 第 2 步：配置管理面 MCP（uvx，凭据三选一）

写入所用客户端的 `mcpServers` 配置（opencode：`opencode.jsonc`；Claude Desktop：
`claude_desktop_config.json`；Cursor：`.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "rds-supabase-mgr": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr",
        "mcp-huaweicloud-rds-supabase-mgr"
      ],
      "env": {
        "SUPABASE_RDS_ENDPOINT": "<discover 生成或人工确认>",
        "HUAWEICLOUD_PROJECT_ID": "<discover 勾选>",
        "HUAWEICLOUD_ACCESS_KEY": "<从受保护文件复制，勿在对话粘贴>",
        "HUAWEICLOUD_SECRET_KEY": "<从受保护文件复制>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

REST Token 模式：删除 AK/SK 两行，改放 `HUAWEICLOUD_AUTH_TOKEN`；完整变量表见
[管理面 README](../../../server/mcp_server_rds_supabase_mgr/README.md)。

**凭据注入三选一**（Agent 按此顺序尝试）：

1. **devkit（推荐）**：宿主已装华为云 devkit 并登录 → 凭据由 devkit 注入，Agent 全程
   不见明文；检测不到 devkit 再走 2。
2. **discover 勾选**：凭据已在环境或受保护文件 → 运行发现命令，把输出的
   `suggested_env`（项目 ID + 推导入口）写入上面的模板，用户从候选中勾选一个：

   ```bash
   uv run --directory server/mcp_server_rds_supabase_mgr \
     python -m mcp_server_supabase.diagnostics discover --probe
   ```

3. **半自动兜底**：Agent 生成含 `<...>` 占位符的配置骨架 → 用户自己从受保护文件把
   真实值复制进 env → 重启客户端。Agent 不索取、不回显、不落盘任何明文；连通与否
   以下一步的只读调用结果为准。

**初始安全态**：`HUAWEICLOUD_MCP_READ_ONLY=true` + `SUPABASE_ENABLE_WRITES=false`
（只读起步）。真实变更时由操作方显式改这两个变量并重启——Agent 不得自行修改。

**region 说明**：frontend/OBS 侧（KooCLI）另需 `HUAWEICLOUD_REGION` + AK/SK——安装阶段
不强制，但建站流程 ① 阶段会做配置完备性检查，缺失项会显示让你填写；届时 endpoint
若推导不了，也会要求你显式指定。

### 第 3 步：验证管理面

1. 重启客户端/重载 MCP 配置（首次 uvx 拉取依赖需稍候）
2. Agent 应看到 29 个工具（以版本对应 README 工具清单为准）
3. 只读试探：`get_supabase_capabilities` 正常返回
4. （可选）discover 的 `--probe` 已确认（endpoint + 项目 + 凭据）三元组可达

### 第 4 步：数据面 MCP——不安装（声明）

告诉用户：数据面 MCP 将在首次建站流程的 ② 阶段由 web-build 技能自动动态安装
（届时实例已创建，网关 URL 与 API Key 就绪）。现在**不要**配置 `rds-supabase`
条目，也不要索取实例信息。安装过程与断点状态记录在项目根 `.hwsupabase/webapp.json`。

### 第 5 步：完成报告

向用户汇报四项：已装技能清单；管理面工具数与只读状态；数据面"② 阶段动态安装"的
约定；触发语句。

## 凭据红线（贯穿全程）

- 密钥只写入本地客户端配置（env），不进仓库、不进日志、不进对话
- Agent 不索取、不回显、不落盘明文；对话中只出现占位符与工具调用结果
- 受保护文件权限 0600；交付/轮换流程见管理面 README"安全机制"
- service_role key 将在 ② 阶段注入数据面（绕过 RLS），仅进可信宿主环境

## 更新与卸载

- **更新**：`git pull` 后重新复制技能目录；uvx 每次拉取默认分支最新（生产建议在
  args 中 pin `@<commit>`）；管理面执行账本（`SUPABASE_STATE_FILE`）跨升级保持同一
  文件，勿切新账本重放
- **卸载**：删除技能目录 → 移除 `mcpServers` 中 `rds-supabase-mgr` 条目 →
  `~/.local/state/huaweicloud-supabase/`（本地执行账本）删除前先审计执行历史

## 常见问题

| 问题 | 处置 |
|---|---|
| GitHub / PyPI 不可达 | 配置企业镜像（pip index-url、UV_INDEX）；或克隆仓库后 `uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr` 本地运行，不经 uvx git 拉取 |
| 多项目账号 | discover 列出全部候选（名称/区域/推导入口），用户勾选；不静默选择 |
| Windows | env 设置用 `$env:`；其余步骤一致 |
| 已有 RDS Supabase 实例 | 跳过创建：触发时说明"使用已有实例"，① 阶段只做配置核对与密钥确认 |
| 什么时候才能访问站点 | ⓪–⑥ 全流程由技能驱动，实例创建（①）可能耗时数分钟；⑥ 通过三层上线清单后给出 stable_url |

## 触发

安装完成后，直接说：

> 帮我建一个博客网站，支持登录评论。
> 搭一个带 AI 问答的知识库应用。

技能从 ⓪ 需求澄清开始接管；流水线、强制门、断点续作与上线验收由
[rds-supabase-web-build](SKILL.md) 编排。
