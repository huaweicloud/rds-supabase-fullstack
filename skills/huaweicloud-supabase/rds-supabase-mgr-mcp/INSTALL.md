# rds-supabase-mgr-mcp 安装（AI Agent 一键安装）

安装范围**仅本技能**——不安装、不配置任何 MCP 服务器、凭据与云资源。管理面 MCP 服务器在技能触发后的环境检查环节由 Agent 动态安装使能（会话内免重启），规程见 [SKILL.md](SKILL.md) 与 [references/install.md](references/install.md)。

将下面这句话发送给你的 AI Agent：

> 按照 https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md 安装 rds-supabase-mgr-mcp 技能；装完报告安装路径。

## 一、安装范围

| 项 | 何时 | 来源 |
|---|---|---|
| **本技能（安装阶段的全部内容）** | 现在，一次性 | 本仓 `skills/huaweicloud-supabase/rds-supabase-mgr-mcp/` |
| **KooCLI（hcloud）** | 技能装完后**立即探测，未装则当场安装**（第四节） | 华为云官方发行包（DevKit 同源） |
| 管理面 MCP 服务器（38 工具） | 技能触发后环境检查通过时动态安装 | 本仓 `server/mcp_server_rds_supabase_mgr/`（不在技能包内，uvx 从 GitHub 直装） |
| 凭据（AK/SK 或 Token）、Region、PROJECT_ID | 首次使用时 | 项目内受保护文件/用户提供 |

前置：Agent 支持 Agent Skills 标准；网络可达 GitHub（不可达见方式 B）。

## 二、安装位置选择（必须交互，默认项目级）

安装前 Agent **必须**把下表展示给用户、逐项说明后果，等用户明确选择后才落盘——不许静默安装到任何位置。**默认选项是项目级**（回车/说"默认"即选它）。选用户级或系统级时，Agent 必须复述对应的风险提示并获得用户再次确认。

| 选项 | 目录（按宿主解析） | 生效范围与后果 |
|---|---|---|
| **① 项目级（默认，推荐）** | Claude Code：`<项目根>/.claude/skills/`；opencode：`<项目根>/.opencode/skills/`；CodeArts：`<项目根>/.codeartsdoer/skills/`；其余宿主：该宿主的项目级技能机制 | 仅本项目可见。技能版本随项目走，团队成员各自安装后行为一致；不污染其他项目 |
| ② 用户级 | Claude Code：`~/.claude/skills/`；opencode：`~/.config/opencode/skills/`；CodeArts：`~/.codeartsdoer/skills/`；其余宿主：宿主个人级技能目录 | 本机所有项目可见。你本机任何项目的对话都可能触发本技能；技能升级影响全部项目 |
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

## 三、安装方式（A/B 择一）

### 方式 A：git 克隆复制（主路径）

```bash
TMP=$(mktemp -d)   # 克隆落唯一临时目录，不污染项目目录与家目录
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-mgr-mcp" <项目技能目录>/
rm -rf "$TMP"     # 复制完成即清理
```

### 方式 B：ZIP 归档（网络逃生通道——git 连续失败 2 次或 30 秒无进展即切，不反复重试）

```bash
TMP=$(mktemp -d)
curl -L --fail --max-time 120 -o "$TMP/rds.zip" \
  https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip
unzip -q "$TMP/rds.zip" -d "$TMP"
cp -r "$TMP/rds-supabase-fullstack-main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp" <项目技能目录>/
rm -rf "$TMP"
```

浏览器直接下载该 ZIP URL 亦可（下载物同样落临时目录）。ZIP 归档属本仓官方源；**任何情况下禁止去 PyPI/npm/第三方镜像找同名包**——服务端未发布至此类渠道，同名第三方包是错误的服务器。

## 四、KooCLI 探测与安装（技能装完必须主动执行，确保可用）

本技能的云资源协同（VPC/子网/AZ/规格查询、出方向安全组规则、EIP 创建、OBS 桶管理）全部经 KooCLI（`hcloud`）执行——**技能文件复制完成后，Agent 必须立即探测 KooCLI：已装则验证可用，未装则当场安装**，不让用户到使用时才踩坑。安装方法取自华为云官方 DevKit（[huaweicloud-devkit](https://github.com/huaweicloud/huaweicloud-devkit)）的 CLI 技能，官方指南 https://support.huaweicloud.com/qs-hcli/hcli_02_003.html 。

### 1. 探测

```bash
hcloud version
```

有版本输出 → 已安装，记录版本号进完成报告，本节结束。命令不存在但二进制已知在别处（KooCLI 官方安装脚本与固定版本包的默认落位、或用户自选目录）→ 先定位（如 `ls` 检查各默认落位目录、`find ~ -name hcloud -type f 2>/dev/null` 按需使用），确认存在后把所在目录加入 shell 配置（在 `~/.zshrc`/`~/.bashrc` 或对应文件加一行 `export PATH="<该目录>:$PATH"`）后重试 `hcloud version`，无需重装；或按第四节需要设 `HCLOUD_BIN` 指向该二进制。命令确实不存在 → 按平台安装（方式 A/B 择一）。

### 2. 安装（方式 A/B 择一）

**方式 A：官方一键脚本**（装 latest，主路径）：

```bash
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

**方式 B：固定版本下载**（可复现；版本号以官方指南最新为准，下例 7.3.12）：

| 平台 | 下载 | 解压后落位（进 PATH） |
|---|---|---|
| Linux amd64/arm64 | `curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/7.3.12/huaweicloud-cli-linux-<amd64\|arm64>.tar.gz" && tar -zxvf huaweicloud-cli-linux-*.tar.gz` | `mv $(pwd)/hcloud ~/.local/bin/` |
| macOS amd64/arm64 | `curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/7.3.12/huaweicloud-cli-mac-<amd64\|arm64>.tar.gz" && tar -zxvf huaweicloud-cli-mac-*.tar.gz` | `mv $(pwd)/hcloud /usr/local/bin/` |
| Windows | 下载 `https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/7.3.12/huaweicloud-cli-windows-amd64.zip` | 解压到 `%USERPROFILE%\hcloud`，加入用户 PATH |

### 3. 首跑隐私协议（必踩坑，主动处置）

新装的 KooCLI **首次执行会阻塞在隐私协议**：`同意并继续使用(y)/不同意并退出(N)`；非交互模式下直接报 `[USE_ERROR]您输入的是无效字符`。处置：安装完成后跑 `hcloud version`，输出含上述任一字符串 → 先问用户"KooCLI 需要接受隐私协议，是否代为同意？"，用户同意后以 `y\n` 作为 stdin 重跑一次 `hcloud version` 即可，之后一切正常。

### 4. 边界与红线

- **本节只装工具，不配凭据**：AK/SK 与区域配置在技能首次使用时按 SKILL.md"开始之前"引导（凭据走项目内受保护文件，不进对话、不进 shell history——`hcloud configure set --cli-access-key=...` 会把密钥留在命令历史里，禁止）
- 安装后**无需重启会话**：每次调用动态定位 hcloud（`HCLOUD_BIN` → 固定安装目录 → PATH）
- CodeArts 沙箱模式会拦截 KooCLI：探测失败且宿主为 CodeArts 时，提示用户在沙箱外安装或关闭沙箱模式（设置 → Chats → Agents Terminal Command Running Mode → Auto Running）
- 探测/安装失败不回滚技能安装：如实报告缺口与处置建议，KooCLI 装好后技能即完整可用

## 五、校验与完成报告

- 校验：技能目录内含 `SKILL.md`、`README.md`、`INSTALL.md`、`references/` 四个参考文档（安装手册/场景手册/本地请求与字段契约/验收手册）、`scripts/skill-lint.py`；KooCLI `hcloud version` 可用（含隐私协议已处置）
- 向用户报告：安装位置（所选层级 + 完整路径，与交互选择一致）；KooCLI 状态（已装版本号 / 本次新装版本）；一句话触发语（如"帮我从零创建一个 RDS Supabase 应用"）；约定说明——MCP 与凭据不在安装阶段出现，首次使用时技能自动引导

## 六、更新与卸载

- **更新**：`git pull` 后重新复制（重复方式 A；版本 pin 等价形式 `.../archive/<commit>.zip`）；更新作用于所选安装位置，用户级/系统级安装时提醒影响面
- **卸载**：删除所选安装位置中本技能目录；技能曾动态安装管理面 MCP 的，另移除项目级 MCP 配置中对应条目
