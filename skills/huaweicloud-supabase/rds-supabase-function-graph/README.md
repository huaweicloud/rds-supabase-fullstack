# rds-supabase-function-graph（RDS Supabase FunctionGraph 云函数技能）

为 RDS Supabase Web 应用承载 **Postgres RPC 装不下的服务端业务逻辑**：交易通知、对接外部系统、复杂领域逻辑、高安全隐私处理。生成零依赖 Node.js 函数 → 经 KooCLI（`hcloud`）部署到华为云 FunctionGraph → 共享版 APIG 触发器暴露 HTTPS 端点 → **函数内验签 Supabase GoTrue JWT** → `fgs-gate.py` 机械核验"无认证请求必须被拒绝"等安全事实。

技能独立可用：云操作全部经 KooCLI 完成，不依赖任何 MCP 服务器与其他技能。

## 快速安装（独立安装）

### 方式一：自然语言安装（推荐）

将下面这句话发送给你的 AI Agent：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/rds-supabase-function-graph/` 复制到本项目的项目级技能目录（禁止装入个人级或系统级目录），安装完成后报告安装路径。

各宿主的项目级技能目录：Claude Code 为 `<项目根>/.claude/skills/`，opencode 为 `<项目根>/.opencode/skills/`，CodeArts 为 `<项目根>/.codeartsdoer/skills/`；其余宿主使用其项目级技能机制。

### 方式二：手动安装

```bash
TMP=$(mktemp -d)
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-function-graph" <项目技能目录>/
rm -rf "$TMP"
```

网络不可达时改用 ZIP 归档下载：把上述 git clone 替换为下载 `https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip` 并解压，复制解压目录下 `skills/huaweicloud-supabase/rds-supabase-function-graph`。禁止使用 `npx skills add` 等包管理器安装——技能包未发布至此类渠道。

## 使用

触发语句示例：

> 给我的博客网站加一个交易通知云函数：下单后异步通知发货系统，需要幂等防重放

技能自动执行：环境检查（KooCLI/认证/命令面自校准）→ 逻辑分解确认 → 样板代码生成 → 部署（OBS 私有制品 + APIG 触发器）→ **安全验证与发布**（无认证 401 / 坏 JWT 401 / 真 JWT 200 / CORS 精确 origin 机器核验 + 版本别名固化）→ 前端联调（fetch 封装 + 幂等重放验证）。

前置条件：KooCLI（hcloud）已安装并认证；已有可用的 RDS Supabase 应用（用户提供接入地址）；OBS 桶可用。

## 前端安全调用链（v1 · 共享版 APIG 路线）

```
前端（GoTrue JWT）
  ↘ APIG 触发器（auth=none，v1 唯一入口形态）
      ↘ 函数内：验签（FGS_JWT_SECRET）→ 精确 CORS → 幂等 → 统一错误契约
```

密钥只存函数环境变量（`--cli-json-file` 由用户组装，agent 不见明文）；升级路径（专享版 APIG 鉴权器 / DEW CSMS / VPC 直连）见 `references/secret-management.md` 附录。

## 文档

- [SKILL.md](SKILL.md)：六步工作流、执行纪律与 fetch 封装契约（agent 入口）
- `references/`：workflow-stages（playbook）、project-state（functions.json 契约）、routing-matrix（判定矩阵）、cli-commands（命令链）、secret-management（密钥纪律）
- `template/`：零依赖 Node.js 18 样板（验签/CORS/幂等/REST/错误契约 + 本地事件回放）
- `scripts/fgs-gate.py`：独立验证门 · `tests/`：21 用例 pytest
