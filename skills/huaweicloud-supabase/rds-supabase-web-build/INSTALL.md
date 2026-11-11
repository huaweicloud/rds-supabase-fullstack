# rds-supabase 技能包安装（AI Agent 一键安装）

面向 AI Agent 的安装指导。用户对 Agent 说：

> 按 INSTALL.md 安装 rds-supabase 技能包，装完告诉我怎么触发。

Agent 按本文四节执行；人类可照读自查。安装范围**仅技能包**——不安装、不配置任何 MCP、凭据与云资源。

## 一、安装范围

| 项 | 何时 | 来源 |
|---|---|---|
| **技能包（全部技能，安装阶段的全部内容）** | 现在，一次性 | 本 GitHub 源码仓 `skills/huaweicloud-supabase/` |
| 管理面 MCP（29 工具） | 工作流步骤三动态启动 | 本仓 `server/`（不在技能包内） |
| 数据面 MCP（38 工具） | 工作流步骤四动态安装 | 同上；依赖步骤三交付的实例凭据 |
| 凭据 / Region / 接入点 / PROJECT_ID | 工作流步骤一 | 项目内 `.hwsupabase/`（项目级隔离） |

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

## 二、安装目录（各宿主差异）

**强约束：只装项目级技能目录**——技能版本随项目走，不污染其他项目与本机全局。

| 宿主 | 项目级技能目录（唯一允许） | 禁止的个人级目录（同名不同根） |
|---|---|---|
| CodeArts | `<项目根>/.codeartsdoer/skills/` | `~/.codeartsdoer/skills` |
| opencode | `<项目根>/.opencode/skills/` | `~/.config/opencode/skills` |
| Claude Code | `<项目根>/.claude/skills/` | `~/.claude/skills` |
| 其余宿主 | 该宿主的项目级技能机制（Agent 自知位置，以项目根为界） | 一切系统级与个人级目录 |

- 系统内置/系统级目录一律禁止；CodeArts 两级目录同名不同根，家目录下属个人级、严禁使用
- 安装路径仅本文两条（git 克隆 / ZIP 归档）；**禁用 `npx skills add` 等一切 CLI/包管理器自动安装**——技能包未发布至此类来源渠道，命令不可用；Agent 不得自行尝试

## 三、三步安装

### 第 1 步 · 安装技能文件（方式 A/B 择一）

**方式 A**（git 克隆复制，主路径）：

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/"* <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

**方式 B**（网络逃生通道——git 失败即切，不反复重试）：连续失败 2 次或 30 秒无进展即判失败 → 下载 ZIP 归档解压：

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/"* <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；版本 pin 等价形式 `.../archive/<commit>.zip`。

安装的全部技能（7 个）：`rds-supabase-web-build`（编排）、`rds-supabase-mgr-mcp`、`rds-supabase-mcp`、`rds-supabase-usage`、`rds-supabase-frontend`、`rds-supabase-postgres-best-practices`、`rds-supabase-function-graph`。

### 第 2 步 · 校验

每个技能目录含 `SKILL.md`；克隆了仓库的，可运行
`uv run --directory server/mcp_server_rds_supabase python ../../scripts/validate_skills.py`，
期望输出 `validate-skills: OK (8 skills)`。

### 第 3 步 · 完成报告

向用户汇报三项：已装技能清单；触发语句示例（如"帮我建一个博客网站"）；约定说明——MCP 与凭据不在安装阶段出现，首次建站时技能从步骤一环境检查开始逐项处理。

## 四、更新与卸载

- **更新**：`git pull` 后重新复制（重复第 1 步）
- **卸载**：删除项目级技能目录；工作流曾配置 MCP 的，另移除项目级 MCP 配置中对应条目

## 常见问题

| 问题 | 处置 |
|---|---|
| GitHub 不可达 | 方式 B（ZIP 逃生通道）或浏览器直接下载；内网可配企业镜像后再走方式 A |
| 装完没有 MCP 与工具 | 预期行为：MCP 由工作流步骤三/四动态安装，凭据由步骤一处理，触发建站即自动进行 |
| 已有 RDS Supabase 实例 | 无需预配置：步骤三交互勾选「使用已有」，随即获取网关 URL 与 API Key |
| 多项目共用一台机器 | 各项目独立 `.hwsupabase/`（凭据与环境配置项目级隔离）；新项目不会识别到其他项目的配置 |
| 何时能访问站点 | 步骤一–九流水线由技能驱动（步骤九三层上线验收后给出 stable_url；实例创建耗时数分钟） |

安装完成后触发：

> 帮我建一个博客网站，支持登录评论。

技能从步骤一环境检查与配置开始接管，编排逻辑见 [SKILL.md](SKILL.md)；MCP 安装来源见 [README.md](README.md)。
