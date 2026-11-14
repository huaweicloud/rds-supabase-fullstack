# rds-supabase-web-build 安装（AI Agent 一键安装）

面向 AI Agent 的安装指导。用户对 Agent 说：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-web-build/INSTALL.md ，安装 rds-supabase-web-build 技能；装完告诉我如何触发建站。

Agent 按本文四节执行。安装范围**仅本技能**——不安装、不配置任何 MCP、凭据与云资源；MCP 与凭据在九步工作流内按需动态安装（见下表）。

## 一、安装范围

| 项 | 何时 | 来源 |
|---|---|---|
| **本技能（安装阶段的全部内容）** | 现在，一次性 | 本 GitHub 源码仓 `skills/huaweicloud-supabase/rds-supabase-web-build/` |
| 管理面 MCP（29 工具） | 工作流步骤三动态启动 | 本仓 `server/`（不在技能包内） |
| 数据面 MCP（38 工具） | 工作流步骤四动态安装 | 同上；依赖步骤三交付的实例凭据 |
| 凭据 / Region / 接入点 / PROJECT_ID | 工作流步骤一 | 项目内 `.hwsupabase/`（项目级隔离） |

**编排依赖说明**：本技能是编排者，步骤路由指向六个专项技能（mgr-mcp / mcp / usage / frontend / postgres-best-practices / function-graph，均在 `skills/huaweicloud-supabase/` 下）。路由目标缺失时对应环节如实降级：提示用户安装该专项技能后继续，或按能力边界自行执行可直接完成的部分。完整编排体验建议连带安装全部技能。

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

## 二、安装位置选择（必须交互，默认项目级）

安装前 Agent **必须**把下表展示给用户、等用户明确选择后才落盘——不许静默安装到任何位置。**默认选项是项目级**（回车/说"默认"即选它）。选用户级或系统级时，Agent 必须复述对应的风险提示并获得用户再次确认。本技能是编排者，安装位置同时决定六个被编排技能的推荐落位（连带安装时保持同一层级）。

| 选项 | 目录（按宿主解析） | 生效范围与后果 |
|---|---|---|
| **① 项目级（默认，推荐）** | CodeArts：`<项目根>/.codeartsdoer/skills/`；opencode：`<项目根>/.opencode/skills/`；Claude Code：`<项目根>/.claude/skills/`；其余宿主：该宿主的项目级技能机制 | 仅本项目可见。九步状态机与路由目标在同一项目内一致；凭据与 MCP 配置（恒为项目级）同界 |
| ② 用户级 | CodeArts：`~/.codeartsdoer/skills/`；opencode：`~/.config/opencode/skills/`；Claude Code：`~/.claude/skills/`；其余宿主：宿主个人级技能目录 | 本机所有项目可见。任何项目说"建个网站"都会触发本技能；升级影响全部项目 |
| ③ 系统级 | 宿主的系统级/内置技能目录（若存在） | 本机所有用户、所有项目可见。影响面最大，一般仅管理员统一预装时使用 |

交互示例：

```
请选择技能安装位置（默认 ①）：
① 项目级（推荐）：<项目根>/.claude/skills/     —— 仅本项目生效
② 用户级：        ~/.claude/skills/            —— 本机全部项目生效，升级影响所有项目
③ 系统级：        <宿主系统级技能目录>          —— 全机所有用户生效，影响面最大
```

风险提示（用户选 ②③ 时必须复述）：
- 用户级/系统级会把技能暴露给无关项目与无关用户，本项目后续升级、卸载都会波及它们
- CodeArts 的 `~/.codeartsdoer/skills` 与项目级 `<项目根>/.codeartsdoer/skills` 同名不同根，极易装错——选 ② 时逐字核对完整路径
- 凭据与 MCP 配置始终只在项目级（本技能红线），装到用户级/系统级不会改变这一点

- 安装路径仅本文两条（git 克隆 / ZIP 归档）；**禁用 `npx skills add` 等一切 CLI/包管理器自动安装**——技能包未发布至此类来源渠道，命令不可用；Agent 不得自行尝试

## 三、三步安装

### 第 1 步 · 安装技能文件（方式 A/B 择一）

**方式 A**（git 克隆复制，主路径）：

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-web-build" <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

（连带安装全部技能时，把复制源换成 `"$TMP/repo/skills/huaweicloud-supabase/"*`。）

**方式 B**（网络逃生通道——git 失败即切，不反复重试）：连续失败 2 次或 30 秒无进展即判失败 → 下载 ZIP 归档解压：

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/rds-supabase-web-build" <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；版本 pin 等价形式 `.../archive/<commit>.zip`。

### 第 2 步 · 校验

技能目录内含 `SKILL.md`、`README.md`、`INSTALL.md`、`USER_GUIDE_REPORT.md`、`assets/framework.svg`、`references/`、`scripts/`、`tests/`。

### 第 3 步 · 完成报告

向用户汇报三项：安装路径；触发语句示例（如"帮我建一个博客网站"）；约定说明——MCP 与凭据不在安装阶段出现，首次建站时技能从步骤一环境检查开始逐项处理。

## 四、更新与卸载

- **更新**：`git pull` 后重新复制（重复第 1 步）
- **卸载**：删除项目级技能目录中本技能；工作流曾配置 MCP 的，另移除项目级 MCP 配置中对应条目
