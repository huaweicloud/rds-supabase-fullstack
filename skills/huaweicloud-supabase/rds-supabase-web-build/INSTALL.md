# rds-supabase-web-build 一键安装指导（自然语言安装）

面向想用一句话创建并托管 RDS Supabase Web 应用的用户。**使用方式：把本文档交给你的
AI Agent，对它说：**

> 按 INSTALL.md 安装 rds-supabase 技能包，装完告诉我怎么触发。

Agent 按下述步骤执行即可；人类也可照读自查。安装阶段**只安装技能包**——不需要任何
云资源、凭据或 MCP 配置先行就绪。

## 安装什么（技能包），MCP 何时出现

| 项 | 何时 | 说明 |
|---|---|---|
| **技能包（全部技能）** | 现在，一次性（安装阶段的全部内容） | 从本 GitHub 源码仓克隆/添加到项目技能目录 |
| 管理面 MCP（29 工具） | 工作流**步骤三**动态启动 | 由技能在工作流中安装（同样只从本仓，见下表）；凭据/Region/接入点/PROJECT_ID 由**步骤一**环境检查与配置处理 |
| 数据面 MCP（38 工具） | 工作流**步骤四**动态安装 | 依赖实例网关 URL 与 API Key——实例在步骤三才创建/选定，届时凭据已就绪 |

> **安装阶段不涉及任何 MCP、凭据与云侧配置**。两台 MCP 服务器由技能工作流按需从本仓
> 动态安装；不要在安装时索取凭据、不要预置 mcpServers 占位配置。

## 前置条件（仅安装）

| 项 | 要求 | 说明 |
|---|---|---|
| AI Agent | 支持 Agent Skills 标准 | opencode / Claude Code / Cursor 等 |
| npm（可选） | Node ≥ 18 | 仅 `npx skills add` 需要；无则手动复制 |
| 网络 | 可达 GitHub | 内网环境见"常见问题" |

运行时前置（uv/uvx、Python ≥ 3.10、华为云凭据、npm 构建环境等）不在安装阶段要求——
技能工作流步骤一环境检查会逐项核对并提示补齐。

## 一句话安装

用户对 Agent 说：

> 按 INSTALL.md 安装 rds-supabase 技能包，装完告诉我怎么触发。

Agent 执行以下 3 步。

### 第 1 步：安装技能文件

方式 A（Agent Skills 开放标准，推荐）：

```bash
npx skills add huaweicloud/rds-supabase-fullstack
```

方式 B（手动复制）：克隆仓库，把 `skills/huaweicloud-supabase/` 下所有技能目录完整复制到
项目技能目录（opencode：`~/.config/opencode/skills/`；Claude Code：`~/.claude/skills/`；
其余宿主按其技能机制，Agent 自知位置）：

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack
cp -r rds-supabase-fullstack/skills/huaweicloud-supabase/* <项目技能目录>/
```

安装的全部技能：`rds-supabase-web-build`（编排总指挥）、`rds-supabase-mgr-mcp`、
`rds-supabase-mcp`、`rds-supabase-usage`、`rds-supabase-frontend`、
`rds-supabase-postgres-best-practices`。

### 第 2 步：校验

每个技能目录含 `SKILL.md`；克隆了仓库的，可运行
`uv run --directory server/mcp_server_rds_supabase python ../../scripts/validate_skills.py`，
期望输出 `validate-skills: OK (7 skills)`。

### 第 3 步：完成报告

向用户汇报：已装技能清单、触发语句示例（如"帮我建一个博客网站"）、以及约定说明——
MCP 与凭据不在安装阶段出现，首次建站时技能从步骤一环境检查开始逐项处理。

## MCP 项目地址与安装方式（工作流动态安装时使用；只允许本仓来源）

两台 MCP 由技能工作流动态安装（管理面 → 步骤三、数据面 → 步骤四）。下表供届时直接
复制使用，本地未克隆仓库也不必搜索：

| MCP | 仓内路径 | 入口脚本 | git uvx 模板 | 本地克隆运行 |
|---|---|---|---|---|
| 管理面 `rds-supabase-mgr` | `server/mcp_server_rds_supabase_mgr` | `mcp-huaweicloud-rds-supabase-mgr` | `uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr` | `uv run --directory server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr` |
| 数据面 `rds-supabase` | `server/mcp_server_rds_supabase` | `mcp-server-huaweicloud-rds-supabase` | `uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`（步骤四动态安装） | `uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase` |

> **警示（Agent 必读）**：PyPI 与应用市场存在**同名/相似的第三方 "supabase" MCP 包**——它们不是本项目的服务器。除上表两种来源（git uvx 模板 / 本仓本地路径）外，**不得搜索、安装或引入任何其他来源的 MCP**；发现已配置了其他来源时，先移除再按本表重装。

**版本锁定（生产推荐）**：动态安装时 `--from` 值改为
`git+https://github.com/huaweicloud/rds-supabase-fullstack@<commit 或 tag>#subdirectory=...`，
避免默认分支变更引入未验证行为。**技能目录里没有 `server/` 子目录属预期行为**——
服务器不在技能包内，所有仓内路径引用均应以上表 URL 为准。

**凭据说明**：安装阶段不经手任何凭据。运行时的凭据红线（密钥只进本地客户端 env、
不进对话/日志/仓库、devkit 注入优先、受保护文件 0600）由技能工作流步骤一起执行，
详见 [SKILL.md](SKILL.md) 执行纪律与管理面 README"安全机制"。

## 更新与卸载

- **更新**：`git pull` 后重新复制/重跑 `npx skills add`；uvx 每次拉取默认分支最新
  （生产建议 pin `@<commit>`）；管理面执行账本（`SUPABASE_STATE_FILE`）跨升级保持同一
  文件，勿切新账本重放
- **卸载**：删除技能目录即可；若工作流已配置过 MCP，另移除 `mcpServers` 中对应条目，
  并在删除 `~/.local/state/huaweicloud-supabase/`（本地执行账本）前先审计执行历史

## 常见问题

| 问题 | 处置 |
|---|---|
| GitHub / PyPI 不可达 | 配置企业镜像（pip index-url、UV_INDEX）；或克隆仓库后工作流步骤中改用本地 `uv run --directory server/... <入口脚本>` 运行，不经 uvx git 拉取 |
| 装完为什么没有 MCP/工具 | 属预期：MCP 由技能工作流动态安装（管理面→步骤三、数据面→步骤四），凭据由步骤一环境检查处理。触发建站即自动进行 |
| 多项目账号 | 步骤一 `diagnostics discover` 列出全部候选（名称/区域/推导入口），用户勾选；不静默选择 |
| Windows | env 设置用 `$env:`；其余步骤一致 |
| 已有 RDS Supabase 实例 | 步骤三会先询问"新建还是使用已有"；选已有 → 管理面 `list_supabase_applications` 列出可用应用供用户勾选，随即获取该应用的网关 URL 与 API Key（步骤四数据面安装所必需，不会遗漏） |
| 什么时候才能访问站点 | 步骤一–八 全流程由技能驱动，实例创建（步骤三）可能耗时数分钟；步骤八通过三层上线清单后给出 stable_url |

## 触发

安装完成后，直接说：

> 帮我建一个博客网站，支持登录评论。
> 搭一个带 AI 问答的知识库应用。

技能从步骤一环境检查与配置开始接管，步骤二进入需求澄清；流水线、强制门、断点续作与上线验收由
[rds-supabase-web-build](SKILL.md) 编排。
